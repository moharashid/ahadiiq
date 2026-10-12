from app import models

class RiskService:
    def _check_autorenewal(self, agreement, clause):
        if clause.clause_type == "renewal":
            return models.Risk(
                agreement_id=agreement.id,
                tenant_id=agreement.tenant_id,
                clause_id=clause.id,
                risk_type="auto_renewal",
                severity=3,
                description=(
                    "Agreement renews automatically unless notice is given before expiry. "
                    "Risk of being locked into another term if the renewal deadline is missed."
                ),
            )
        return None

    def _check_missing_expiry(self, agreement):
        if agreement.expiry_date is None:
            return models.Risk(
                agreement_id=agreement.id,
                tenant_id=agreement.tenant_id,
                risk_type="missing_expiry",
                severity=3,
                description=(
                    "No expiry date could be identified. Deadlines and obligations cannot be "
                    "scheduled or tracked, leaving the agreement effectively unmonitored."
                ),
            )
        return None

    def _check_penalty(self, agreement, clause):
        if clause.clause_type == "penalty":
            amount = f" of {clause.amount}" if clause.amount is not None else ""
            return models.Risk(
                agreement_id=agreement.id,
                tenant_id=agreement.tenant_id,
                clause_id=clause.id,
                risk_type="penalty",
                severity=2,
                description=(
                    f"Financial penalty{amount} applies on breach or late performance. "
                    "Non-compliance carries a direct monetary cost."
                ),
            )
        return None

    def _check_short_notice(self, agreement, clause):
        if clause.clause_type in ("notice", "termination") and clause.notice_period is not None:
            if clause.notice_period < 30:
                return models.Risk(
                    agreement_id=agreement.id,
                    tenant_id=agreement.tenant_id,
                    clause_id=clause.id,
                    risk_type="short_notice",
                    severity=2,
                    description=(
                        f"Short notice period of {clause.notice_period} days. Little time to act "
                        "before the clause takes effect, raising the chance of a missed deadline."
                    ),
                )
        return None

    def assess_agreement(self, agreement, clauses):
        risks = []

        for clause in clauses:
            if clause.status != "validated":
                continue
            for rule in (self._check_autorenewal, self._check_penalty, self._check_short_notice):
                risk = rule(agreement, clause)
                if risk is not None:
                    risks.append(risk)

        expiry_risk = self._check_missing_expiry(agreement)
        if expiry_risk is not None:
            risks.append(expiry_risk)

        total = sum(r.severity for r in risks)
        agreement.risk_score = total
        agreement.risk_level = self._level_from_score(total)

        return risks

    def _level_from_score(self, score):
        if score >= 6:
            return "high"
        if score >= 3:
            return "medium"
        return "low"


risk_service = RiskService()