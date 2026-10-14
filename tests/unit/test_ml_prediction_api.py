
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
from threading import Barrier

from fastapi.testclient import TestClient
import jwt
from sqlalchemy import create_engine
from sqlalchemy.engine import result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.dependencies.database import get_db
from backend.core.security import hash_password
from backend.core.config import settings
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
        "total_savings_reported": True,
        "emergency_fund": 60000,
        "emergency_fund_reported": True,
        "investments": 25000,
        "investments_reported": True,
        "total_debt": 80000,
        "total_debt_reported": True,
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
    assert data["total_savings_reported"] is True
    assert data["reported_total_savings"] == 100000
    assert data["reported_emergency_fund"] == 60000


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
        "total_savings_reported": True,
        "emergency_fund": 60000,
        "emergency_fund_reported": True,
        "investments": 25000,
        "investments_reported": True,
        "total_debt": 80000,
        "total_debt_reported": True,
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


def test_profile_balance_provenance_zero_and_partial_updates():
    email = "balance-provenance-api@example.com"
    create_named_test_user(email)
    headers = {"Authorization": f"Bearer {get_test_token(email)}"}

    created = client.put(
        "/me/financial-profile",
        json={
            "monthly_income": 1000,
            "monthly_expenses": 500,
            "monthly_emi": 100,
            # A stored positive number without a status is still unknown.
            "total_savings": 2500,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    profile = created.json()
    assert profile["total_savings"] == "2500.00"  # Legacy key preserved.
    assert profile["total_savings_reported"] is False
    assert profile["reported_total_savings"] is None
    health = client.get("/me/financial-health", headers=headers)
    assert health.status_code == 200
    assert health.json()["total_savings"] == 2500.0
    assert health.json()["reported_total_savings"] is None
    assert health.json()["emergency_fund_months"] is None
    assert health.json()["tracked_net_worth"] is None

    amount_only_update = client.put(
        "/me/financial-profile",
        json={"total_savings": 3000},
        headers=headers,
    )
    assert amount_only_update.status_code == 200
    assert amount_only_update.json()["total_savings"] == "3000.00"
    assert amount_only_update.json()["total_savings_reported"] is False
    assert amount_only_update.json()["reported_total_savings"] is None

    partial = client.put(
        "/me/financial-profile",
        json={"monthly_income": 1100},
        headers=headers,
    )
    assert partial.status_code == 200
    assert partial.json()["total_savings"] == "3000.00"
    assert partial.json()["total_savings_reported"] is False
    assert partial.json()["reported_total_savings"] is None

    invalid_confirmation = client.put(
        "/me/financial-profile",
        json={"total_savings_reported": True},
        headers=headers,
    )
    assert invalid_confirmation.status_code == 422

    confirmed_zero = client.put(
        "/me/financial-profile",
        json={"total_savings": 0, "total_savings_reported": True},
        headers=headers,
    )
    assert confirmed_zero.status_code == 200, confirmed_zero.text
    assert confirmed_zero.json()["total_savings"] == "0.00"
    assert confirmed_zero.json()["total_savings_reported"] is True
    assert confirmed_zero.json()["reported_total_savings"] == "0.00"

    unconfirm = client.put(
        "/me/financial-profile",
        json={"total_savings_reported": False},
        headers=headers,
    )
    assert unconfirm.status_code == 200
    assert unconfirm.json()["total_savings"] == "0.00"
    assert unconfirm.json()["reported_total_savings"] is None


def test_reported_emergency_fund_cannot_exceed_reported_liquid_savings():
    email = "balance-subset-validation@example.com"
    create_named_test_user(email)
    headers = {"Authorization": f"Bearer {get_test_token(email)}"}
    response = client.put(
        "/me/financial-profile",
        json={
            "monthly_income": 1000,
            "monthly_expenses": 500,
            "monthly_emi": 100,
            "total_savings": 100,
            "total_savings_reported": True,
            "emergency_fund": 200,
            "emergency_fund_reported": True,
        },
        headers=headers,
    )
    assert response.status_code == 422


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


def test_simulation_api_auth_scenario_validation_and_profile_immutability():
    email = "simulation-api-integration@example.com"
    create_named_test_user(email)
    token = get_test_token(email)
    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "total_savings": 100000,
        "total_savings_reported": True,
        "emergency_fund": 60000,
        "emergency_fund_reported": True,
        "investments": 25000,
        "investments_reported": True,
        "total_debt": 80000,
        "total_debt_reported": True,
    }
    saved = client.put(
        "/me/financial-profile", json=profile_payload, headers=headers
    )
    assert saved.status_code == 200, saved.text
    before = client.get("/me/financial-profile", headers=headers).json()

    unauthenticated = client.post("/me/simulate", json={"horizon_months": 3})
    assert unauthenticated.status_code == 401

    default_request = client.post("/me/simulate", json={}, headers=headers)
    assert default_request.status_code == 200, default_request.text
    assert default_request.json()["horizon_months"] == 12
    missing_body = client.post("/me/simulate", headers=headers)
    assert missing_body.status_code == 422

    baseline_response = client.post(
        "/me/simulate", json={"horizon_months": 3}, headers=headers
    )
    assert baseline_response.status_code == 200, baseline_response.text
    baseline = baseline_response.json()
    assert baseline["baseline_monthly_cash_flow"] == 15000
    assert len(baseline["baseline"]["months"]) == 3
    assert baseline["scenario"]["months"] == baseline["baseline"]["months"]
    assert {
        "month", "income", "expenses", "emi", "cash_flow_surplus",
        "liquid_savings", "emergency_fund", "investments", "debt",
        "tracked_net_worth",
    }.issubset(baseline["baseline"]["months"][0])
    assert {
        "baseline_monthly_cash_flow", "scenario_monthly_cash_flow",
        "monthly_cash_flow_change", "scenario_emergency_fund",
        "scenario_monthly_income", "baseline", "scenario",
        "monthly_differences",
    }.issubset(baseline)

    scenario_response = client.post(
        "/me/simulate",
        json={
            "horizon_months": 3,
            "recurring_income_change": 1000,
            "recurring_expense_change": 500,
            "recurring_emi_change": 250,
            "changes_start_month": 2,
            "one_time_cost": 10000,
            "one_time_month": 1,
            "one_time_source": "liquid_savings",
        },
        headers=headers,
    )
    assert scenario_response.status_code == 200, scenario_response.text
    scenario = scenario_response.json()
    assert scenario["scenario"]["months"][0]["cash_flow_surplus"] == 15000
    assert scenario["scenario"]["months"][1]["cash_flow_surplus"] == 15250
    assert scenario["scenario"]["months"][0]["one_time_cost"] == 10000

    after = client.get("/me/financial-profile", headers=headers).json()
    assert after == before

    invalid_requests = [
        {"horizon_months": 5},
        {"horizon_months": 3, "scenario_monthly_income": -1},
        {"horizon_months": 3, "one_time_cost": "NaN"},
        {"horizon_months": 3, "recurring_expense_change": "0.001"},
        {"horizon_months": 3, "one_time_source": "unreported_asset"},
        {"horizon_months": 3, "new_loan_principal": 1000},
        {"horizon_months": 3, "new_loan_principal": 1000,
         "new_loan_term_months": 12, "new_loan_start_month": 4},
    ]
    for payload in invalid_requests:
        invalid = client.post("/me/simulate", json=payload, headers=headers)
        assert invalid.status_code == 422, (payload, invalid.text)


def test_simulation_api_requires_saved_profile():
    email = "simulation-api-empty@example.com"
    create_named_test_user(email)
    token = get_test_token(email)
    response = client.post(
        "/me/simulate",
        json={"horizon_months": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_minimum_intervention_api_auth_contract_and_profile_immutability():
    email = "minimum-intervention-api@example.com"
    create_named_test_user(email)
    token = get_test_token(email)
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "total_savings": 100000,
        "total_savings_reported": True,
        "emergency_fund": 60000,
        "emergency_fund_reported": True,
        "investments": 25000,
        "investments_reported": True,
        "total_debt": 80000,
        "total_debt_reported": True,
    }
    saved = client.put("/me/financial-profile", json=profile_payload, headers=headers)
    assert saved.status_code == 200, saved.text
    before = client.get("/me/financial-profile", headers=headers).json()

    unauthenticated = client.post("/me/optimize", json={})
    assert unauthenticated.status_code == 401
    missing_body = client.post("/me/optimize", headers=headers)
    assert missing_body.status_code == 422

    response = client.post(
        "/me/optimize",
        json={
            "target_monthly_surplus": 20000,
            "essential_monthly_expenses": 25000,
            "discretionary_monthly_expenses": 5000,
            "max_expense_reduction": 5000,
            "max_income_increase": 5000,
            "horizon_months": 3,
            "minimum_emergency_fund_runway_months": 1.5,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["feasible"] is True
    assert result["target_monthly_surplus"] == 20000
    assert result["baseline_outcome"]["monthly_cash_flow"] == 15000
    assert len(result["baseline_projection"]["months"]) == 3
    assert len(result["scenario_projection"]["months"]) == 3
    assert result["tied_minimum_options"]
    assert result["search"]["global_optimality_claimed"] is False
    assert {
        "feasible", "target_monthly_surplus", "scenario_monthly_cash_flow",
        "recommended_expense_reduction", "recommended_new_emi_reduction",
        "recommended_income_increase", "total_proposed_adjustment",
    }.issubset(result)

    for invalid_payload in (
        {"horizon_months": 5},
        {"max_income_increase": -1},
        {"max_income_increase": "1.001"},
        {"minimum_emergency_fund_runway_months": "NaN"},
        {"essential_monthly_expenses": 20000},
        {"essential_monthly_expenses": 20000, "discretionary_monthly_expenses": 5000},
    ):
        invalid = client.post("/me/optimize", json=invalid_payload, headers=headers)
        assert invalid.status_code == 422, (invalid_payload, invalid.text)

    after = client.get("/me/financial-profile", headers=headers).json()
    assert after == before

    unconfirmed = client.put(
        "/me/financial-profile",
        json={"emergency_fund_reported": False},
        headers=headers,
    )
    assert unconfirmed.status_code == 200
    unconfirmed_before_optimization = client.get(
        "/me/financial-profile", headers=headers
    ).json()
    unknown_runway = client.post(
        "/me/optimize",
        json={
            "target_monthly_surplus": 15000,
            "horizon_months": 3,
            "minimum_emergency_fund_runway_months": 1.5,
        },
        headers=headers,
    )
    assert unknown_runway.status_code == 200
    assert unknown_runway.json()["feasible"] is False
    assert unknown_runway.json()["constraints_checked"]["emergency_fund_runway_status"] == "unassessed_missing_emergency_fund"
    assert client.get("/me/financial-profile", headers=headers).json() == unconfirmed_before_optimization


def test_registration_is_case_insensitive_and_login_normalizes_email():
    response = client.post(
        "/auth/register",
        json={"email": "CaseSensitive@Example.com", "password": "Long-Test-Password-1"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "casesensitive@example.com"

    duplicate = client.post(
        "/auth/register",
        json={"email": "CASESENSITIVE@example.com", "password": "Long-Test-Password-2"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/auth/login",
        data={"username": "CASESENSITIVE@EXAMPLE.COM", "password": "Long-Test-Password-1"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_expired_jwt_is_rejected():
    email = "expired-token-test@example.com"
    create_named_test_user(email)
    with TestingSessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        user_id = user.id
    expired = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get(
        "/me/financial-profile",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401


def test_authenticated_users_can_only_read_and_modify_their_own_profiles():
    first_email = "tenant-one@example.com"
    second_email = "tenant-two@example.com"
    create_named_test_user(first_email)
    create_named_test_user(second_email)
    first_headers = {"Authorization": f"Bearer {get_test_token(first_email)}"}
    second_headers = {"Authorization": f"Bearer {get_test_token(second_email)}"}

    first_profile = {
        "monthly_income": 50000, "monthly_expenses": 30000, "monthly_emi": 5000,
        "total_savings": 80000, "emergency_fund": 40000,
        "investments": 20000, "total_debt": 60000,
    }
    second_profile = {
        "monthly_income": 25000, "monthly_expenses": 12000, "monthly_emi": 3000,
        "total_savings": 15000, "emergency_fund": 10000,
        "investments": 5000, "total_debt": 20000,
    }
    assert client.put("/me/financial-profile", json=first_profile, headers=first_headers).status_code == 200
    assert client.put("/me/financial-profile", json=second_profile, headers=second_headers).status_code == 200
    second_before = client.get("/me/financial-profile", headers=second_headers).json()

    own_update = client.put(
        "/me/financial-profile",
        json={"monthly_income": 60000},
        headers=first_headers,
    )
    assert own_update.status_code == 200
    assert own_update.json()["monthly_income"] == "60000.00"
    assert client.get("/me/financial-profile", headers=second_headers).json() == second_before
    assert client.get("/me/financial-health", headers=second_headers).json()["monthly_income"] == 25000

    balance_confirmation = client.put(
        "/me/financial-profile",
        json={"total_savings": 80000, "total_savings_reported": True},
        headers=first_headers,
    )
    assert balance_confirmation.status_code == 200
    assert balance_confirmation.json()["reported_total_savings"] == "80000.00"
    assert client.get("/me/financial-profile", headers=second_headers).json() == second_before

    hypothetical = client.post(
        "/me/simulate",
        json={"horizon_months": 3, "recurring_income_change": 5000},
        headers=first_headers,
    )
    assert hypothetical.status_code == 200
    first_after_simulation = client.get("/me/financial-profile", headers=first_headers).json()
    assert first_after_simulation["monthly_income"] == "60000.00"
    assert first_after_simulation["reported_total_savings"] == "80000.00"
    assert client.get("/me/financial-profile", headers=second_headers).json() == second_before


def test_case_insensitive_email_unique_index_handles_concurrent_inserts():
    # Pytest's default temp directory is outside the writable workspace in the
    # sandbox. Give this test its own uniquely named file inside the workspace.
    descriptor, database_path = tempfile.mkstemp(
        prefix="email-uniqueness-", suffix=".sqlite", dir=Path.cwd()
    )
    os.close(descriptor)
    isolated_engine = create_engine(
        f"sqlite:///{Path(database_path).as_posix()}",
        connect_args={"timeout": 10},
    )
    User.__table__.create(isolated_engine)
    barrier = Barrier(2)

    def insert_email(email):
        barrier.wait(timeout=5)
        try:
            with isolated_engine.begin() as connection:
                connection.execute(
                    User.__table__.insert().values(
                        email=email,
                        password_hash="test-hash-not-a-real-credential",
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                    )
                )
            return "created"
        except IntegrityError:
            return "duplicate"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(insert_email, [
                "Concurrent@Example.com", "concurrent@example.com"
            ]))
        assert sorted(outcomes) == ["created", "duplicate"]
    finally:
        isolated_engine.dispose()
        Path(database_path).unlink(missing_ok=True)
