import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from agents.resume_analyzer import analyze_resume
from agents.job_matcher import calculate_match
from agents.ats_optimizer import optimize_for_ats
from agents.roadmap_agent import generate_roadmap
from agents.mock_interview import generate_questions, evaluate_answer
from agents.cover_letter import generate_cover_letter
from agents.salary_predictor import predict_salary
import tempfile, os

app = Server("career-copilot")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="analyze_resume",
            description="Extract structured info from a resume PDF/DOCX file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to resume PDF or DOCX"}
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="match_job",
            description="Calculate how well a resume matches a job description",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "job_description": {"type": "string"}
                },
                "required": ["file_path", "job_description"]
            }
        ),
        types.Tool(
            name="optimize_ats",
            description="Optimize resume for ATS systems based on job description",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "job_description": {"type": "string"}
                },
                "required": ["file_path", "job_description"]
            }
        ),
        types.Tool(
            name="generate_roadmap",
            description="Create a week-by-week learning roadmap for missing skills",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "job_description": {"type": "string"}
                },
                "required": ["file_path", "job_description"]
            }
        ),
        types.Tool(
            name="mock_interview",
            description="Generate interview questions tailored to resume and job",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "job_description": {"type": "string"}
                },
                "required": ["file_path", "job_description"]
            }
        ),
        types.Tool(
            name="generate_cover_letter",
            description="Write a personalized cover letter",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "job_description": {"type": "string"},
                    "company_name": {"type": "string"}
                },
                "required": ["file_path", "job_description"]
            }
        ),
        types.Tool(
            name="predict_salary",
            description="Predict salary range based on resume and job",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "job_description": {"type": "string"},
                    "location": {"type": "string"}
                },
                "required": ["file_path", "job_description"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    file_path = arguments.get("file_path", "")
    jd = arguments.get("job_description", "")

    if name == "analyze_resume":
        result = analyze_resume(file_path)
    elif name == "match_job":
        resume = analyze_resume(file_path)
        result = calculate_match(resume, jd)
    elif name == "optimize_ats":
        resume = analyze_resume(file_path)
        match = calculate_match(resume, jd)
        result = optimize_for_ats(resume, jd, match["missing_skills"])
    elif name == "generate_roadmap":
        resume = analyze_resume(file_path)
        match = calculate_match(resume, jd)
        result = generate_roadmap(resume, jd, match["missing_skills"])
    elif name == "mock_interview":
        resume = analyze_resume(file_path)
        result = generate_questions(resume, jd)
    elif name == "generate_cover_letter":
        resume = analyze_resume(file_path)
        result = generate_cover_letter(resume, jd, arguments.get("company_name", "the company"))
    elif name == "predict_salary":
        resume = analyze_resume(file_path)
        result = predict_salary(resume, jd, arguments.get("location", "India"))
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())