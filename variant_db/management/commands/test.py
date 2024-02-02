import variant_db.management.commands.workbook as workbook
import variant_db.management.commands.insert as insert
wb_dict = workbook.read_workbook("misc/sample_new_format_SP.csv")
print(wb_dict[0])
insert.insert_row(wb_dict[0])