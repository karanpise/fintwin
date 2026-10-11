
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import result
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.dependencies.database import get_db
from backend.core.security import hash_password
from database.connection import Base
from database.models import User
    
import math

# Use your project's actual declarative Base import if different.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def create_test_user():
    with TestingSessionLocal() as db:
        existing = db.query(User).filter_by(
            email="ml-test@example.com"
        ).first()
        if existing:
            return

        user = User(
            email="ml-test@example.com",
            password_hash=hash_password("Test-Only-Password-123!"),
        )
        db.add(user)
        db.commit()


def test_ml_prediction_requires_authentication():
    response = client.post(
        "/ml/predict-risk",
        json={"features": {}},
    )
    assert response.status_code in (401, 403)


def test_health_endpoint_is_available():
    response = client.get("/health")
    assert response.status_code == 200


def test_authenticated_ml_prediction():
    create_test_user()

    login_response = client.post(
        "/auth/login",
        data={
            "username": "ml-test@example.com",
            "password": "Test-Only-Password-123!",
        },
    )
    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    features = {
        "age": 23,
        "employment_type": "Salaried",
        "employment_years": 1.1,
        "monthly_income": 43515.0,
        "monthly_expenses": 27142.0,
        "monthly_emi": 3359.0,
        "monthly_savings": 13014.0,
        "total_savings": 237122.0,
        "emergency_fund": 89754.0,
        "investments": 122539.0,
        "total_debt": 200556.0,
        "dependents": 2,
        "insurance": "Yes",
        "health_insurance": "Yes",
        "income_stability_score": 73.3,
        "financial_goal": "Car",
        "investment_experience": "Beginner",
        "expected_salary_growth_pct": 7.5,
        "expected_expense_inflation_pct": 4.2,
        "planned_major_expense": "Car",
        "planned_expense_month": 9,
    }

    response = client.post(
        "/ml/predict-risk",
        json={"features": features},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text

    result = response.json()
    print("Prediction response:", result)

    


    # Validate the prediction response
    assert result["predicted_risk"] in {"Low", "Medium", "High"}
    assert result["model"] == "logistic_regression"
    assert result["status"] == "experimental"
    assert result["disclaimer"]

    probabilities = result["class_probabilities"]

    assert set(probabilities) == {"Low", "Medium", "High"}
    assert all(
        isinstance(p, (int, float))
        and math.isfinite(p)
        and 0 <= p <= 1
        for p in probabilities.values()
    )
    assert math.isclose(
        sum(probabilities.values()),
        1.0,
        abs_tol=0.001,
    ), "Class probabilities should sum to approximately 1"
    assert result["predicted_risk"] == max(
        probabilities,
        key=probabilities.get,
)


def create_named_test_user(email: str):
    """Create a separate test user if one does not already exist."""
    with TestingSessionLocal() as db:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            return

        user = User(
            email=email,
            password_hash=hash_password("Test-Only-Password-123!"),
        )
        db.add(user)
        db.commit()


def get_test_token(email: str) -> str:
    """Log in a test user and return the JWT access token."""
    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "Test-Only-Password-123!",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_financial_health_requires_authentication():
    response = client.get("/me/financial-health")
    assert response.status_code in (401, 403)


def test_financial_health_without_profile_returns_404():
    email = "financial-health-empty@example.com"
    create_named_test_user(email)
    token = get_test_token(email)

    response = client.get(
        "/me/financial-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Create your financial profile first"


def test_financial_health_returns_expected_metrics():
    email = "financial-health-profile@example.com"
    create_named_test_user(email)
    token = get_test_token(email)
    headers = {"Authorization": f"Bearer {token}"}

    # Create this user's financial profile through the public API.
    profile_payload = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "total_savings": 100000,
        "emergency_fund": 60000,
        "investments": 25000,
        "total_debt": 80000,
    }

    save_response = client.put(
        "/me/financial-profile",
        json=profile_payload,
        headers=headers,
    )
    assert save_response.status_code == 200, save_response.text

    response = client.get(
        "/me/financial-health",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["monthly_income"] == 50000
    assert data["monthly_expenses"] == 30000
    assert data["monthly_emi"] == 5000
    assert data["monthly_cash_flow"] == 15000
    assert data["savings_rate_percent"] == 30.0
    assert data["debt_to_income_percent"] == 10.0
    assert data["emergency_fund_months"] == 1.71
    assert data["total_savings"] == 100000
    assert data["emergency_fund"] == 60000
    assert data["investments"] == 25000
    assert data["total_debt"] == 80000


def test_financial_profile_requires_authentication():
    response = client.get("/me/financial-profile")
    assert response.status_code in (401, 403)


def test_financial_profile_without_saved_profile_returns_404():
    email = "profile-empty-test@example.com"
    create_named_test_user(email)
    token = get_test_token(email)

    response = client.get(
        "/me/financial-profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_financial_profile_saves_and_returns_optional_planned_expense():
    email = "profile-planned-expense-test@example.com"
    create_named_test_user(email)
    token = get_test_token(email)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "total_savings": 100000,
        "emergency_fund": 60000,
        "investments": 25000,
        "total_debt": 80000,
        "planned_major_expense": None,
        "planned_expense_month": 0,
    }

    saved = client.put(
        "/me/financial-profile",
        json=payload,
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["planned_major_expense"] is None
    assert saved.json()["planned_expense_month"] == 0

    fetched = client.get(
        "/me/financial-profile",
        headers=headers,
    )
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["planned_major_expense"] is None
    assert fetched.json()["planned_expense_month"] == 0


def test_login_rejects_invalid_credentials():
    response = client.post(
        "/auth/login",
        data={
            "username": "unknown-user@example.com",
            "password": "Wrong-Password-123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
