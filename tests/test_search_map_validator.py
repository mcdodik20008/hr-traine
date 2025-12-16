"""Tests for SearchMapValidator"""
import pytest
import pandas as pd
import os
import tempfile
from app.core.search_map import SearchMapValidator


class TestSearchMapValidator:
    """Test SearchMapValidator class"""
    
    def test_validator_initialization(self):
        """Test validator initialization"""
        validator = SearchMapValidator("test.xlsx")
        assert validator.file_path == "test.xlsx"
        assert validator.df is None
        assert validator.errors == []
    
    def test_load_excel_file(self):
        """Test loading Excel file"""
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        f.close()
        try:
            # Create a simple Excel file
            df = pd.DataFrame({
                'Company': ['Company1', 'Company2'],
                'Position': ['Position1', 'Position2'],
                'Source': ['Source1', 'Source2'],
                'Contact': ['Contact1', 'Contact2'],
                'Status': ['Status1', 'Status2']
            })
            df.to_excel(f.name, index=False)
            
            validator = SearchMapValidator(f.name)
            result = validator.load()
            
            assert result is True
            assert validator.df is not None
            assert len(validator.df) == 2
        finally:
            # Try to delete, ignore errors on Windows
            try:
                os.unlink(f.name)
            except (PermissionError, OSError):
                pass
    
    def test_load_csv_file(self):
        """Test loading CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Company,Position,Source,Contact,Status\n")
            f.write("Company1,Position1,Source1,Contact1,Status1\n")
            f.close()
            
            validator = SearchMapValidator(f.name)
            result = validator.load()
            
            assert result is True
            assert validator.df is not None
            
            os.unlink(f.name)
    
    def test_load_unsupported_format(self):
        """Test loading unsupported file format"""
        validator = SearchMapValidator("test.txt")
        result = validator.load()
        
        assert result is False
        assert len(validator.errors) > 0
        assert "Unsupported file format" in validator.errors[0]
    
    def test_validate_structure_valid(self):
        """Test structure validation with valid columns"""
        df = pd.DataFrame({
            'Company': ['Company1'],
            'Position': ['Position1'],
            'Source': ['Source1'],
            'Contact': ['Contact1'],
            'Status': ['Status1']
        })
        
        validator = SearchMapValidator("test.xlsx")
        validator.df = df
        
        result = validator.validate_structure()
        
        assert result is True
        assert len(validator.errors) == 0
    
    def test_validate_structure_missing_columns(self):
        """Test structure validation with missing columns"""
        df = pd.DataFrame({
            'Company': ['Company1'],
            'Position': ['Position1']
        })
        
        validator = SearchMapValidator("test.xlsx")
        validator.df = df
        
        result = validator.validate_structure()
        
        assert result is False
        assert len(validator.errors) > 0
        assert "Missing columns" in validator.errors[0]
    
    def test_validate_structure_no_dataframe(self):
        """Test structure validation without dataframe"""
        validator = SearchMapValidator("test.xlsx")
        
        result = validator.validate_structure()
        
        assert result is False
    
    def test_validate_content_valid(self):
        """Test content validation with valid data"""
        df = pd.DataFrame({
            'Company': ['Company1', 'Company2'],
            'Position': ['Position1', 'Position2'],
            'Source': ['Source1', 'Source2'],
            'Contact': ['Contact1', 'Contact2'],
            'Status': ['Status1', 'Status2']
        })
        
        validator = SearchMapValidator("test.xlsx")
        validator.df = df
        
        report = validator.validate_content()
        
        assert report["valid"] is True
        assert report["total_rows"] == 2
        assert report["empty_contacts"] == 0
    
    def test_validate_content_too_many_empty_contacts(self):
        """Test content validation with too many empty contacts"""
        df = pd.DataFrame({
            'Company': ['Company1', 'Company2', 'Company3'],
            'Position': ['Position1', 'Position2', 'Position3'],
            'Source': ['Source1', 'Source2', 'Source3'],
            'Contact': ['Contact1', None, None],  # 2 out of 3 empty (>50%)
            'Status': ['Status1', 'Status2', 'Status3']
        })
        
        validator = SearchMapValidator("test.xlsx")
        validator.df = df
        
        report = validator.validate_content()
        
        assert report["valid"] is False
        assert len(report["errors"]) > 0
        assert "empty contacts" in report["errors"][0].lower()
    
    def test_validate_content_no_dataframe(self):
        """Test content validation without dataframe"""
        validator = SearchMapValidator("test.xlsx")
        # Ensure df is None
        validator.df = None
        
        report = validator.validate_content()
        
        # If df is None, it should return valid=False
        assert report["valid"] is False
        # The method returns {"valid": False, "errors": self.errors}
        # If errors list is empty, that's also valid behavior - just check valid is False
        assert "errors" in report
    
    def test_get_summary_success(self):
        """Test get_summary with no errors"""
        validator = SearchMapValidator("test.xlsx")
        
        summary = validator.get_summary()
        
        assert "successfully" in summary.lower()
    
    def test_get_summary_with_errors(self):
        """Test get_summary with errors"""
        validator = SearchMapValidator("test.xlsx")
        validator.errors.append("Error 1")
        validator.errors.append("Error 2")
        
        summary = validator.get_summary()
        
        assert "Error 1" in summary
        assert "Error 2" in summary
    
    @pytest.mark.asyncio
    async def test_extract_data_for_llm(self):
        """Test extracting data for LLM"""
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        f.close()
        try:
            df = pd.DataFrame({
                'Company': ['Company1'],
                'Position': ['Position1'],
                'Source': ['Source1'],
                'Contact': ['Contact1'],
                'Status': ['Status1']
            })
            df.to_excel(f.name, index=False)
            
            validator = SearchMapValidator(f.name)
            validator.load()
            
            data = validator.extract_data_for_llm()
            
            assert isinstance(data, dict)
            assert len(data) > 0
        finally:
            try:
                os.unlink(f.name)
            except (PermissionError, OSError):
                pass
    
    @pytest.mark.asyncio
    async def test_extract_data_for_llm_no_dataframe(self):
        """Test extracting data without dataframe"""
        validator = SearchMapValidator("test.xlsx")
        
        data = validator.extract_data_for_llm()
        
        assert data == {}
    
    @pytest.mark.asyncio
    async def test_validate_with_llm(self, mocker):
        """Test LLM validation"""
        # Patch the import in the function
        mock_llm_client = mocker.patch('app.core.llm_client.llm_client')
        mock_llm_client.validate_search_map = mocker.AsyncMock(return_value={
            "valid": True,
            "issues": [],
            "suggestions": []
        })
        
        validator = SearchMapValidator("test.xlsx")
        validator.df = pd.DataFrame({
            'Company': ['Company1'],
            'Position': ['Position1'],
            'Source': ['Source1'],
            'Contact': ['Contact1'],
            'Status': ['Status1']
        })
        
        result = await validator.validate_with_llm()
        
        assert result["valid"] is True
        mock_llm_client.validate_search_map.assert_called_once()

