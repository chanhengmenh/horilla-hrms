import base64
from xhtml2pdf import pisa
from io import BytesIO
import fitz

with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/extracted_img_7_Image30.jpg', 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode('utf-8')
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/extracted_img_0_Image16.png', 'rb') as f:
    empty_b64 = base64.b64encode(f.read()).decode('utf-8')
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/img_checked.png', 'rb') as f:
    checked_b64 = base64.b64encode(f.read()).decode('utf-8')

chk_empty_html = f'<img src="data:image/png;base64,{empty_b64}" width="10" height="7" style="vertical-align: middle;" />'
chk_checked_html = f'<img src="data:image/png;base64,{checked_b64}" width="10" height="7" style="vertical-align: middle;" />'

data = {
    'requisition_code': 'REQ-2026-0013',
    'position_title': 'System Specialist',
    'location': 'RMO Technology Co., Ltd Main Office',
    'function': 'IT Operations',
    'department': 'Technical Department',
    'manager_name': 'Mr. Hybrid IT Manager',
    'manager_position': 'Hybrid IT Manager',
    'requested_date': '14.10.26',
    'employment_type': 'permanent',
    'permanent_category': 'budgeted',
    'replacement_for': '',
    'replacement_reason': '',
    'target_onboarding_date': '01.11.26',
    'position_level': 'Specialist',
    'contract_term': '',
    'period_from': '',
    'period_to': '',
    'working_days_hours': 'Mon - Fri, 8:00 AM - 5:00 PM',
    'justification': 'Install & Configuration Server & Storage, Support Service operation and provide 24/7 service infrastructure stability for enterprise client environments.',
    'position_requirements': 'Bachelor Degree in IT/Computer Science; 3+ years experience with Windows/Linux Servers, VMware virtualization, SAN storage configuration, and backup solutions.',
    'hr_reviewer': 'Ms. Sin Thida',
    'hr_reviewed_date': '14.10.26',
    'approved_by': 'Mr. KHIEU Sarvorneat',
    'approved_date': '14.10.26',
    'status': 'approved'
}

html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Staff Requisition Form - {data['requisition_code']}</title>
    <style>
        @page {{
            size: letter portrait;
            margin-top: 0.22in;
            margin-bottom: 0.15in;
            margin-left: 0.42in;
            margin-right: 0.42in;
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            font-size: 7.5pt;
            color: #000;
            line-height: 1.15;
            margin: 0;
            padding: 0;
        }}
        .main-frame {{
            border: 1.25pt solid #000;
            width: 100%;
        }}
        .banner {{
            background-color: #D0CECE;
            border-top: 0.75pt solid #000;
            border-bottom: 0.75pt solid #000;
            text-align: center;
            font-weight: bold;
            font-size: 7.8pt;
            padding: 2pt 0;
        }}
        .title-banner {{
            background-color: #D0CECE;
            border-top: 1pt solid #000;
            border-bottom: 1pt solid #000;
            text-align: center;
            font-weight: bold;
            font-size: 9.5pt;
            padding: 3pt 0;
        }}
        .table-data {{
            width: 100%;
        }}
        .table-data th, .table-data td {{
            border: 0.75pt solid #000;
            padding: 2.5pt 5pt;
            font-size: 7.3pt;
            vertical-align: middle;
        }}
        .table-data th {{
            font-weight: normal;
            text-align: left;
            background-color: #fff;
        }}
        .val-cell {{
            font-weight: bold;
            font-size: 7.6pt;
            height: 12pt;
        }}
        .approvals-frame {{
            border: 1.25pt solid #000;
            width: 100%;
            margin-top: 5pt;
        }}
        .field-box {{
            border: 0.75pt solid #000;
            height: 11pt;
            line-height: 11pt;
            padding: 0 3pt;
            font-size: 7.3pt;
            font-weight: bold;
        }}
    </style>
</head>
<body>

    <!-- Upper Main Frame -->
    <div class="main-frame">
        
        <!-- Header Logo & Requisition Code Area -->
        <table style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <td style="padding: 2pt 6pt; width: 60%; vertical-align: middle;">
                    <img src="data:image/jpeg;base64,{logo_b64}" width="115" />
                </td>
                <td style="padding: 2pt 6pt; width: 40%; text-align: right; vertical-align: top;">
                    <div style="font-size: 6.8pt; color: #555;">Requisition Code:</div>
                    <div style="font-size: 8.5pt; font-weight: bold; color: #111;">{data['requisition_code']}</div>
                </td>
            </tr>
        </table>

        <!-- Title Banner -->
        <div class="title-banner">
            Staff Requisition Form
        </div>

        <!-- Note Section -->
        <div style="padding: 3pt 6pt; border-bottom: 0.75pt solid #000; font-size: 7.3pt;">
            <strong>Note:</strong><br>
            All fields are mandatory; requisition will be considered only if this form is fully completed.
        </div>

        <!-- Position Details Banner -->
        <div class="banner">
            Position Details
        </div>

        <!-- Position Details Table -->
        <table class="table-data" cellspacing="0" cellpadding="0" style="border-left: none; border-right: none;">
            <tr>
                <th style="width: 38%; border-left: none;">* Position to be requested</th>
                <th style="width: 18%;">* Based Location</th>
                <th style="width: 18%;">* Function</th>
                <th style="width: 26%; border-right: none;">* Department</th>
            </tr>
            <tr>
                <td class="val-cell" style="border-left: none;">{data['position_title']}</td>
                <td class="val-cell">{data['location']}</td>
                <td class="val-cell">{data['function']}</td>
                <td class="val-cell" style="border-right: none;">{data['department']}</td>
            </tr>
        </table>

        <!-- Line Manager's Details Banner -->
        <div class="banner" style="border-top: none;">
            Line Manager's Details
        </div>

        <!-- Line Manager's Details Table -->
        <table class="table-data" cellspacing="0" cellpadding="0" style="border-left: none; border-right: none;">
            <tr>
                <th style="width: 56%; border-left: none;">* Manager's Name</th>
                <th style="width: 44%; border-right: none;">Position</th>
            </tr>
            <tr>
                <td class="val-cell" style="border-left: none;">{data['manager_name']}</td>
                <td class="val-cell" style="border-right: none;">{data['manager_position']}</td>
            </tr>
        </table>

        <!-- Employment Status Banner -->
        <div class="banner" style="border-top: none;">
            Employment Status
        </div>

        <!-- Employment Status Content -->
        <div style="padding: 4pt 8pt; border-bottom: 0.75pt solid #000; font-size: 7.3pt;">
            
            <table style="width: 100%;" cellspacing="0" cellpadding="0">
                <tr>
                    <!-- Permanent Options (Left) -->
                    <td style="width: 58%; vertical-align: top;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['employment_type'] == 'permanent' else chk_empty_html}</td>
                                <td style="font-weight: bold; vertical-align: middle;">PERMANENT</td>
                            </tr>
                        </table>

                        <table cellspacing="0" cellpadding="0" style="margin-left: 14pt; margin-top: 2pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['permanent_category'] == 'budgeted' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Additional Headcount Budgetted</td>
                            </tr>
                            <tr>
                                <td style="width: 14pt; vertical-align: middle; padding-top: 2pt;">{chk_checked_html if data['permanent_category'] == 'non_budgeted' else chk_empty_html}</td>
                                <td style="vertical-align: middle; padding-top: 2pt;">Additional Headcount - Non-Budgetted</td>
                            </tr>
                        </table>

                        <table cellspacing="0" cellpadding="0" style="margin-left: 14pt; margin-top: 2pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['permanent_category'] == 'replacement' else chk_empty_html}</td>
                                <td style="width: 80pt; vertical-align: middle;">Replacement for</td>
                                <td style="width: 125pt;"><div class="field-box">{data['replacement_for']}</div></td>
                            </tr>
                            <tr>
                                <td></td>
                                <td style="vertical-align: middle; padding-top: 2pt;">Reason(s):</td>
                                <td style="padding-top: 2pt;"><div class="field-box">{data['replacement_reason']}</div></td>
                            </tr>
                        </table>
                    </td>

                    <!-- Right Column (Dates & Levels) -->
                    <td style="width: 42%; vertical-align: top; padding-left: 8pt;">
                        <table cellspacing="0" cellpadding="0" style="margin-top: 10pt;">
                            <tr>
                                <td style="width: 95pt; vertical-align: middle;">Target onboarding date:</td>
                                <td style="width: 60pt;"><div class="field-box" style="text-align: center;">{data['target_onboarding_date']}</div></td>
                            </tr>
                            <tr>
                                <td style="vertical-align: middle; padding-top: 3pt;">Position Level:</td>
                                <td style="padding-top: 3pt;"><div class="field-box" style="text-align: center;">{data['position_level']}</div></td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Contract / Intern Row -->
            <table cellspacing="0" cellpadding="0" style="margin-top: 3pt;">
                <tr>
                    <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['employment_type'] == 'contract' else chk_empty_html}</td>
                    <td style="width: 55pt; vertical-align: middle;">Contract</td>
                    <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['employment_type'] == 'intern' else chk_empty_html}</td>
                    <td style="vertical-align: middle;">INTERN</td>
                </tr>
            </table>

            <!-- Full Time / Part Time Sub-Box -->
            <table cellspacing="0" cellpadding="0" style="width: 96%; border: 0.75pt solid #41719c; margin-top: 2pt; margin-bottom: 2pt;">
                <tr>
                    <td style="padding: 2pt 5pt; width: 35%;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['contract_term'] == 'full_time' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Full Time</td>
                            </tr>
                        </table>
                    </td>
                    <td style="padding: 2pt 5pt; width: 65%;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['contract_term'] == 'part_time' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Part Time</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Employment Period -->
            <table cellspacing="0" cellpadding="0" style="margin-top: 2pt;">
                <tr>
                    <td style="width: 95pt; vertical-align: middle;">Employment Period from:</td>
                    <td style="width: 70pt;"><div class="field-box" style="text-align: center;">{data['period_from']}</div></td>
                    <td style="width: 20pt; text-align: center; vertical-align: middle;">To:</td>
                    <td style="width: 70pt;"><div class="field-box" style="text-align: center;">{data['period_to']}</div></td>
                </tr>
            </table>

            <!-- Working Day & Hour -->
            <table cellspacing="0" cellpadding="0" style="margin-top: 2pt;">
                <tr>
                    <td style="width: 95pt; vertical-align: middle;">Working Day & Hour:</td>
                    <td style="width: 210pt;"><div class="field-box">{data['working_days_hours']}</div></td>
                </tr>
            </table>

        </div>

        <!-- Justification Banner -->
        <div class="banner" style="border-top: none;">
            Justification (Why is this position needed?)
        </div>
        <div style="padding: 3pt 6pt; min-height: 22pt; border-bottom: 0.75pt solid #000; font-size: 7.3pt;">
            {data['justification']}
        </div>

        <!-- Position Requirements Banner -->
        <div class="banner" style="border-top: none;">
            Position Requirements (refer to JD attached)
        </div>
        <div style="padding: 3pt 6pt; min-height: 32pt; font-size: 7.3pt;">
            {data['position_requirements']}
        </div>

    </div>

    <!-- Approvals Frame -->
    <div class="approvals-frame">
        <div class="banner" style="border-top: none;">
            Approvals
        </div>
        <table style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <td style="width: 33.3%; padding: 4pt 8pt; vertical-align: top; font-size: 7.3pt;">
                    <strong>Requested by (hiring manager)</strong>
                    <div style="height: 22pt; padding-top: 5pt; font-style: italic;">
                        {data['manager_name']}
                    </div>
                    <div>Date: &nbsp; {data['requested_date']}</div>
                </td>
                <td style="width: 33.3%; padding: 4pt 8pt; vertical-align: top; font-size: 7.3pt;">
                    <strong>Checked HR Rep</strong>
                    <div style="height: 22pt; padding-top: 5pt; font-style: italic;">
                        {data['hr_reviewer']}
                    </div>
                    <div>Date: &nbsp; {data['hr_reviewed_date']}</div>
                </td>
                <td style="width: 33.4%; padding: 4pt 8pt; vertical-align: top; font-size: 7.3pt;">
                    <strong>Approved by CEO</strong>
                    <div style="height: 22pt; padding-top: 5pt; font-style: italic;">
                        {data['approved_by']}
                    </div>
                    <div>Date: &nbsp; {data['approved_date']}</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Footer -->
    <table style="width: 100%; margin-top: 2pt;" cellspacing="0" cellpadding="0">
        <tr>
            <td style="width: 50%;"></td>
            <td style="width: 50%; text-align: right; font-size: 6.8pt; line-height: 1.15; color: #000;">
                RMO-HRA-QF-001<br>
                Revision 001<br>
                01.06.24
            </td>
        </tr>
    </table>

</body>
</html>'''

out = BytesIO()
pisa_status = pisa.CreatePDF(html_content, dest=out)
pdf_data = out.getvalue()
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/test_rmo_single_page.pdf', 'wb') as f:
    f.write(pdf_data)

doc = fitz.open(stream=pdf_data, filetype='pdf')
print('PAGES IN GENERATED PDF:', len(doc))
