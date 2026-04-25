import pandas as pd
from app.models.schemas import AnalysisResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ExcelExporter:
    @staticmethod
    def export(df: pd.DataFrame, analysis: AnalysisResult, file_path: str):
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Sheet 1: Transactions
            df.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Sheet 2: Monthly Summary
            monthly_df = pd.DataFrame([m.model_dump() for m in analysis.monthly_summary])
            monthly_df.to_excel(writer, sheet_name='Monthly Summary', index=False)
            
            # Sheet 3: Category Summary
            cat_df = pd.DataFrame([c.model_dump() for c in analysis.category_summary])
            cat_df.to_excel(writer, sheet_name='Category Summary', index=False)
            
            # Auto-adjust column widths
            for sheetname in writer.sheets:
                worksheet = writer.sheets[sheetname]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"Excel report generated at {file_path}")