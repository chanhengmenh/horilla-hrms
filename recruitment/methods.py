"""
methods.py

This page is used to write reusable methods.

"""

from recruitment.models import Recruitment, RecruitmentSurvey


def is_stagemanager(request):
    """
    This method is used to check stage manager, if the employee is also
    recruitment manager it returns true
    """
    try:
        employee = request.user.employee_get
        return employee.recruitment_set.exists() or employee.stage_set.exists()
    except Exception:
        return False


def is_recruitmentmanager(request):
    """
    This method is used to check the employee is recruitment manager or not
    """
    try:
        employee = request.user.employee_get
        return employee.recruitment_set.exists()
    except Exception:
        return False


def stage_manages(request, stage):
    """
    This method is used to check the employee manager to this stage."""
    try:
        employee = request.user.employee_get

        return (
            stage.stage_manager.filter(id=employee.id).exists()
            or stage.recruitment_id.recruitment_managers.filter(id=employee.id).exists()
        )
    except Exception:
        return False


def recruitment_manages(request, recruitment):
    """
    This method is used to check the employee is manager to the current recruitment
    """
    try:
        employee = request.user.employee_get
        return recruitment.recruitment_managers.filter(id=employee.id).exists()
    except Exception:
        return False


def update_rec_template_grp(upt_template_ids, template_groups, rec_id):
    recruitment_obj = Recruitment.objects.get(id=rec_id)
    if list(upt_template_ids) != list(template_groups):
        recruitment_surveys = RecruitmentSurvey.objects.filter(recruitment_ids=rec_id)
        if recruitment_surveys:
            for survey in recruitment_surveys:
                survey.recruitment_ids.remove(rec_id)
                survey.save()
        if upt_template_ids:
            rec_surveys_templates = RecruitmentSurvey.objects.filter(
                template_id__in=upt_template_ids
            )
            for survey in rec_surveys_templates:
                survey.recruitment_ids.add(recruitment_obj)


def in_all_managers(request):
    """
    Check the user in any recruitment/onboarding related managers
    """
    return (
        request.user.employee_get.stage_set.exists()
        or request.user.employee_get.recruitment_set.exists()
        or request.user.employee_get.onboardingstage_set.exists()
        or request.user.employee_get.onboarding_task.exists()
    )


def extract_text_from_jd_file(file_input, filename=""):
    """
    Extracts plain text content from an uploaded Job Description document.
    Supports .docx (Word), .pdf, and plain text (.txt / .md).
    Pure-Python in-memory parsing with zero external binary dependencies.
    """
    import io
    import os
    import re

    fname = (filename or getattr(file_input, "name", "") or str(file_input)).lower()

    # Read binary content
    data = None
    if isinstance(file_input, (str, os.PathLike)):
        try:
            with open(file_input, "rb") as f:
                data = f.read()
        except Exception:
            return ""
    elif hasattr(file_input, "read"):
        try:
            pos = file_input.tell() if hasattr(file_input, "tell") else 0
            data = file_input.read()
            if hasattr(file_input, "seek"):
                file_input.seek(pos)
        except Exception:
            return ""
    elif isinstance(file_input, (bytes, bytearray)):
        data = bytes(file_input)

    if not data:
        return ""

    # 1. DOCX (WordprocessingML in ZIP container)
    if fname.endswith(".docx") or data[:4] == b"PK\x03\x04":
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" in z.namelist():
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = []
                    for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                        texts = [
                            node.text
                            for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                            if node.text
                        ]
                        line = "".join(texts).strip()
                        if line:
                            paragraphs.append(line)
                    if paragraphs:
                        return "\n".join(paragraphs)
        except Exception:
            pass

    # 2. PDF Document
    if fname.endswith(".pdf") or data[:4] == b"%PDF":
        try:
            import pymupdf

            doc = pymupdf.open(stream=data, filetype="pdf")
            pages_text = [page.get_text().strip() for page in doc if page.get_text().strip()]
            doc.close()
            if pages_text:
                return "\n\n".join(pages_text)
        except Exception:
            try:
                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(data))
                pages_text = [p.extract_text() for p in reader.pages if p.extract_text()]
                if pages_text:
                    return "\n\n".join(pages_text)
            except Exception:
                pass

    # 3. Plain text / Markdown
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            decoded = data.decode(enc).strip()
            if decoded:
                return decoded
        except Exception:
            continue

    return ""

