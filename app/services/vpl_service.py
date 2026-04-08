# app/services/vpl_service.py
import httpx
from typing import Dict, Any

class VPLService:
    def __init__(self, jail_url: str = "http://localhost:8080"):
        self.jail_url = jail_url
    
    async def execute_code(
        self, 
        code: str, 
        language: str, 
        stdin_input: str = ""
    ) -> Dict[str, Any]:
        """Execute code in VPL sandbox"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.jail_url}/execute",
                json={
                    "code": code,
                    "language": language,
                    "stdin": stdin_input
                }
            )
            return response.json()
    
    async def run_tests(
        self, 
        code: str, 
        language: str, 
        test_cases: list
    ) -> Dict[str, Any]:
        """Run test cases against student code"""
        results = []
        passed = 0
        
        for test in test_cases:
            result = await self.execute_code(
                code=code,
                language=language,
                stdin_input=test.get("input", "")
            )
            
            is_correct = result.get("output", "").strip() == test.get("expected_output", "").strip()
            if is_correct:
                passed += 1
            
            results.append({
                "test_input": test.get("input"),
                "expected_output": test.get("expected_output"),
                "actual_output": result.get("output"),
                "passed": is_correct,
                "execution_time": result.get("execution_time")
            })
        
        return {
            "passed": passed,
            "total": len(test_cases),
            "score": (passed / len(test_cases)) * 100,
            "results": results
        }