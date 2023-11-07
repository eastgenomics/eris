# trying to standardize the way we write history into db


class History:
    def __init__(self):
        pass

    # automation
    def flag_clinical_indication_panel(reason: str) -> str:
        return f"Flagged for manual review - {reason}"

    def auto_created_clinical_indication_panel() -> str:
        return "Auto-created ci-panel link"

    # creation
    def panel_gene_created() -> str:
        return f"PanelGene record created"

    def clinical_indication_panel_created() -> str:
        return f"ClinicalIndicationPanel record created"

    # modification
    def panel_gene_metadata_changed(
        field: str,
        old_value: str,
        new_value: str,
    ) -> str:
        return f"PanelGene metadata {field} changed from {old_value} to {new_value}"

    def clinical_indication_panel_metadata_changed(
        field: str,
        old_value: str,
        new_value: str,
    ) -> str:
        return f"ClinicalIndicationPanel metadata {field} changed from {old_value} to {new_value}"

    def clinical_indication_metadata_changed(
        field: str, old_value: str, new_value: str
    ) -> str:
        return f"ClinicalIndication metadata {field} changed from {old_value} to {new_value}"

    def clinical_indication_panel_activated(
        ci_id: str,
        panel_id: str,
        review: bool = False,
    ) -> str:
        return f"ClinicalIndicationPanel linking clinical indication {ci_id} to panel {panel_id} activated online {'by review' if review else ''}"

    def clinical_indication_panel_deactivated(
        ci_id: str,
        panel_id: str,
        review: bool = False,
    ) -> str:
        return f"ClinicalIndicationPanel linking clinical indication {ci_id} to panel {panel_id} deactivated online {'by review' if review else ''}"

    def panel_gene_flagged_due_to_confidence(
        confidence_level: str,
    ) -> str:
        return f"PanelGene flagged for manual review - confidence level dropped to {confidence_level}"

    def panel_gene_approved(user) -> str:
        return f"PanelGene approved by {user}"

    def panel_gene_reverted(user) -> str:
        return f"PanelGene reverted by {user}"

    # gene/HGNC releases
    def gene_hgnc_release_approved_symbol_change() -> str:
        return f"HGNC approved symbol has changed"
    
    def gene_hgnc_release_alias_symbol_change() -> str:
        return f"HGNC alias symbol has changed"
    
    def gene_hgnc_release_new() -> str:
        return f"HGNC gene has been added for the first time"
    
    def gene_hgnc_release_unchanged() -> str:
        return f"HGNC gene is unchanged in this release"
