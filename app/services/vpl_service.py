# app/services/vpl_service.py
from asyncio import subprocess
import os
import tempfile

import httpx
from typing import Dict, Any

class VPLService:
    def __init__(self, jail_url: str = "http://localhost:8080"):
        self.jail_url = jail_url
    
    # async def execute_code(
    #     self, 
    #     code: str, 
    #     language: str, 
    #     stdin_input: str = ""
    # ) -> Dict[str, Any]:
    #     """Execute code in VPL sandbox"""
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(
    #             f"{self.jail_url}/execute",
    #             json={
    #                 "code": code,
    #                 "language": language,
    #                 "stdin": stdin_input
    #             }
    #         )
    #         return response.json()
    
    async def execute_code(
        self, 
        code: str, 
        language: str, 
        stdin_input: str = ""
    ) -> dict:
        """Execute code with proper stdin handling using subprocess"""
        
        if language == "python":
            try:
                # Create a temporary file for the code
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                
                # Run the Python script with the provided stdin
                process = subprocess.run(
                    ['python', temp_file],
                    input=stdin_input,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )
                
                # Clean up temp file
                os.unlink(temp_file)
                
                return {
                    "output": process.stdout,
                    "error": process.stderr if process.stderr else None,
                    "execution_time": 100
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "output": "",
                    "error": "Execution timed out (30 seconds)",
                    "execution_time": 30000
                }
            except Exception as e:
                return {
                    "output": "",
                    "error": str(e),
                    "execution_time": 0
                }
        else:
            return {
                "output": f"Code execution for {language} is not yet implemented.",
                "error": None,
                "execution_time": 50
            }

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