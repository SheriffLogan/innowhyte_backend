import time
from google import genai
from google.genai import types
import re
from app.schema.schema_classes import *

client = genai.Client(api_key="AIzaSyCTPbtvn2PwnkGzcGGhodEgcVn09dYHO5w")


def parse_full_summary(full_summary: str):
    """
    Parse the full summary text (returned by Gemini) into separate sections.
    Expected format:
      1. [Heading 1] - [Summary text]
      2. [Heading 2] - [Summary text]
      3.1 [Subheading 1] - [Summary text]
      3.2 [Subheading 2] - [Summary text]
      4. [Heading 3] - [Summary text]
    """
    try:
        first_section = re.search(r'\d+\.', full_summary)
        if first_section:
            full_summary = full_summary[first_section.start():]
        # Updated regex that matches a trailing period optionally.
        pattern = re.compile(
            r'^(\d+(?:\.\d+)*\.?)\s+(.*?)\s*(?:\((?:Page|page)\s*(\d+)\))?\s*-\s*(.*)$',
            re.MULTILINE
        )        
        sections = []
        for match in pattern.finditer(full_summary):
            num = match.group(1).strip()  # e.g., "1." or "3.1"
            heading = match.group(2).strip()
            page = int(match.group(3)) if match.group(3) else None
            summary = match.group(4).strip()
            full_heading = f"{num} {heading}"
            sections.append({
                "section": full_heading,
                "summary": summary,
                "page": page
            })
        return sections
    except Exception as e:
        raise Exception(f"Error parsing summary: {str(e)}")

# document understanding function with prompt.
def gemini_document_understanding(pdf_bytes: bytes) -> str:
    prompt = (
        "Analyze the attached PDF document. Identify the main sections and, if present, their subsections along with their headings. "
        "Generate a structured summary for each section using one of the following formats exactly:\n\n"
        "Format A (if there are no clear subsections):\n"
        "1. [Main Heading] - [Summary]\n"
        "2. [Main Heading] - [Summary]\n\n"
        "Format B (if clear subsections are present):\n"
        "Either output the main section with a summary, followed by numbered subsections, for example:\n"
        "1. [Main Heading] - [Summary]\n"
        "1.1 [Subheading 1] - [Summary]\n"
        "1.2 [Subheading 2] - [Summary]\n\n"
        "OR, if the main section summary is not necessary, then output only the subsections starting directly with sub-headings, for example:\n"
        "1.1 [Subheading 1] - [Summary]\n"
        "1.2 [Subheading 2] - [Summary]\n\n"
        "Ensure that if a section does not have subsections, no sub-section numbering is included. "
        "Do not include any extraneous text."
        "Additionally, for each section or subsection, include the page number where it starts in parentheses before the summary. "
        "For example:\n"
        "1. Introduction (Page 2) - Summarizes the background and goals of the paper.\n"
        "3.1 Model Design (Page 5) - Explains the architecture and logic.\n"
        "**Only include the page number if it can be determined accurately.**"
    )
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'),
                prompt
            ]
    )
        print(f"Full PDF Summary: {response.text}")
        return response.text
    except Exception as e:
        raise Exception(f"Error generating document understanding: {str(e)}")



# streaming function that splits the full summary into sections and yields SSE messages.
def gemini_stream_document_summary(pdf_bytes: bytes):
    try:
        full_summary = gemini_document_understanding(pdf_bytes)
    except Exception as e:
        # If the document understanding fails, yield an error message and exit.
        yield ErrorResponse(message=str(e)).json()
        return

    try:
        sections = parse_full_summary(full_summary)
        print(f"Parsed Sections: {sections}")
    except Exception as e:
        yield ErrorResponse(message=str(e)).json()
        return

    total_sections = len(sections)
    if total_sections == 0:
        yield ErrorResponse(message="No sections parsed from document.").json()
        return

    for i, sec in enumerate(sections):
        overall_progress = int(((i + 1) / total_sections) * 100)
        try:
            # Yield the section data as a SectionResponse
            section_msg = SectionResponse(
                section=sec["section"],
                summary=sec["summary"],
                page=sec.get("page")
            )
            yield section_msg.json() + "\n\n"
        except Exception as e:
            yield ErrorResponse(message=f"Error processing section {sec['section']}: {str(e)}").json() + "\n\n"
        try:
            # Yield an overall progress update as a ProgressResponse.
            progress_msg = ProgressResponse(progress=overall_progress)
            yield progress_msg.json() + "\n\n"
        except Exception as e:
            yield ErrorResponse(message=f"Error sending progress update: {str(e)}").json() + "\n\n"
        time.sleep(0.5)  # Simulate slight delay for streaming

