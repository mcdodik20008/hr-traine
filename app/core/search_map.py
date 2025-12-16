import pandas as pd
from typing import List, Dict, Any, Optional
import os

class SearchMapValidator:
    REQUIRED_COLUMNS = [
        "Company", "Position", "Source", "Contact", "Status"
    ]

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df: Optional[pd.DataFrame] = None
        self.errors: List[str] = []

    def load(self) -> bool:
        try:
            if self.file_path.endswith('.csv'):
                self.df = pd.read_csv(self.file_path)
            elif self.file_path.endswith(('.xls', '.xlsx')):
                self.df = pd.read_excel(self.file_path)
            else:
                self.errors.append("Unsupported file format")
                return False
            return True
        except Exception as e:
            self.errors.append(f"Failed to load file: {str(e)}")
            return False

    def validate_structure(self) -> bool:
        if self.df is None:
            return False
        
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in self.df.columns]
        if missing_cols:
            self.errors.append(f"Missing columns: {', '.join(missing_cols)}")
            return False
        return True

    def validate_content(self) -> Dict[str, Any]:
        """
        Performs basic content validation.
        Returns a dictionary with validation results.
        """
        if self.df is None:
            return {"valid": False, "errors": self.errors}

        report = {
            "total_rows": len(self.df),
            "empty_contacts": 0,
            "suspicious_status": 0,
            "valid": True,
            "errors": []
        }

        # Example checks
        if "Contact" in self.df.columns:
            report["empty_contacts"] = self.df["Contact"].isna().sum()
        
        # Logic: If too many empty contacts, flag it
        if report["empty_contacts"] > len(self.df) * 0.5:
            report["errors"].append("Too many empty contacts (>50%)")
            report["valid"] = False

        return report
    
    def extract_data_for_llm(self) -> dict:
        """
        Extract key data from Excel for LLM validation.
        Returns structured dict with relevant fields.
        """
        if self.df is None:
            return {}
        
        # Try to extract data from different sheets if available
        try:
            import pandas as pd
            
            # Read all sheets
            excel_file = pd.ExcelFile(self.file_path)
            all_data = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(self.file_path, sheet_name=sheet_name)
                # Convert to dict, handling NaN values
                sheet_data = {}
                for col in df.columns:
                    values = df[col].dropna().tolist()
                    if values:
                        sheet_data[col] = values if len(values) > 1 else values[0]
                all_data[sheet_name] = sheet_data
            
            return all_data
        except Exception as e:
            # Fallback: use main dataframe
            return {"Main": self.df.to_dict()}
    
    async def validate_with_llm(self) -> Dict[str, Any]:
        """
        Use LLM to validate logical consistency of search map.
        Returns validation report from LLM.
        """
        from app.core.llm_client import llm_client
        
        excel_data = self.extract_data_for_llm()
        if not excel_data:
            return {"valid": False, "issues": ["Could not extract data from file"], "suggestions": []}
        
        return await llm_client.validate_search_map(excel_data)

    def get_summary(self) -> str:
        if not self.errors:
            return "File loaded successfully."
        return "\n".join(self.errors)
