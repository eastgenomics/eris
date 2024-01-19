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
        return "PanelGene record created"

    def clinical_indication_panel_created() -> str:
        return "ClinicalIndicationPanel record created"

    def clinical_indication_superpanel_created() -> str:
        return "ClinicalIndicationSuperPanel record created"

    # modification
    def panel_gene_metadata_changed(
        field: str,
        old_value: str,
        new_value: str,
    ) -> str:
        return f"PanelGene metadata {field} changed from {old_value} to {new_value}"

    # clinical indication panel
    def clinical_indication_panel_new_td_link(
        new_value: str,
    ) -> str:
        return (
            f"ClinicalIndicationPanel linked to new test directory release: {new_value}"
        )

    def clinical_indication_metadata_changed(
        field: str, old_value: str, new_value: str
    ) -> str:
        return f"ClinicalIndication metadata {field} changed from {old_value} to {new_value}"

    def clinical_indication_panel_activated(
        id: str,
        review: bool = False,
    ) -> str:
        return (
            f"ClinicalIndicationPanel {id} activated online" + " by review"
            if review
            else ""
        )

    def clinical_indication_panel_deactivated(
        id: str,
        review: bool = False,
    ) -> str:
        return (
            f"ClinicalIndicationPanel {id} deactivated online" + " by review"
            if review
            else ""
        )

    def clinical_indication_panel_reverted(
        id: str,
        old_value: str,
        new_value: str,
        review: bool = False,
    ) -> str:
        return (
            f"ClinicalIndicationPanel {id} reverted from {old_value} to {new_value}"
            + " by review"
            if review
            else ""
        )

    def clinical_indication_panel_approved(id: str) -> str:
        return f"ClinicalIndicationPanel {id} approved by review"

    # clinical indication superpanel
    def clinical_indication_superpanel_reverted(
        id: str,
        metadata: str,
        old_value: str,
        new_value: str,
        review: bool = False,
    ) -> str:
        return (
            f"ClinicalIndicationSuperPanel {id} metadata '{metadata}' reverted from {old_value} to {new_value}"
            + " by review"
            if review
            else ""
        )

    def clinical_indication_superpanel_approved(id: str) -> str:
        return f"ClinicalIndicationSuperPanel {id} approved by review"

    # panel gene
    def panel_gene_flagged_due_to_confidence(
        confidence_level: str,
    ) -> str:
        return f"PanelGene flagged for manual review - confidence level dropped to {confidence_level}"

    def panel_gene_approved(user) -> str:
        return f"PanelGene approved by {user}"

    def panel_gene_reverted(user) -> str:
        return f"PanelGene reverted by {user}"

    # test directory history
    def td_added() -> str:
        return "New td version added"

    def panel_ci_autolink() -> str:
        return "Panel has automatically been linked to an existing ClinicalIndication - test directory version applied automatically"

    def td_panel_ci_autolink(new_td) -> str:
        return f"Panel-ClinicalIndication linked to a new TestDirectoryRelease {new_td}"

    def td_superpanel_ci_autolink(new_td) -> str:
        return f"SuperPanel-ClinicalIndication linked to a new TestDirectoryRelease {new_td}"

    # gene/HGNC releases
    def gene_hgnc_release_approved_symbol_change(old_value: str, new_value: str) -> str:
        return f"HGNC approved symbol has changed from {old_value} to {new_value}"

    def gene_hgnc_release_alias_symbol_change(old_value: str, new_value: str) -> str:
        return f"HGNC alias symbol has changed from {old_value} to {new_value}"

    def gene_hgnc_release_new() -> str:
        return "HGNC gene has been added for the first time"

    def gene_hgnc_release_present() -> str:
        return "HGNC gene is present in this release"

    # transcript/gff releases
    def tx_gff_release_new() -> str:
        return "Transcript added from a GFF release for the first time"

    def tx_gff_release_present() -> str:
        return "Transcript is present in this release"
