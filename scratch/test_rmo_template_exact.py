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

chk_empty = f'<img src="data:image/png;base64,{empty_b64}" width="10" height="7" />'
chk_checked = f'<img src="data:image/png;base64,{checked_b64}" width="10" height="7" />'

data = {
    'requisition_code': 'REQ-2026-0013',
    'position_title': 'System Specialist',
    'location': 'RMO Technology Co., Ltd Main Office',
    'function': 'Technical Department - Systems & Infrastructure',
    'department': 'Technical Department',
    'manager_name': 'Sophea Chan',
    'manager_position': 'Hybrid IT Manager',
    'requested_date': '14.10.26',
    'employment_type': 'permanent',
    'permanent_category': 'budgeted',
    'replacement_for': '',
    'replacement_reason': '',
    'target_onboarding_date': '13.11.26',
    'position_level': 'Specialist',
    'contract_term': '',
    'period_from': '',
    'period_to': '',
    'working_days_hours': 'Mon - Fri, 8:00 AM - 5:00 PM',
    'justification': 'Install & Configuration Server & Storage, Support Service operation. The Technical Department requires dedicated infrastructure systems expertise to ensure high availability, enterprise virtualization administration (VMware vSphere/vCenter), Windows Server / Active Directory governance, and proactive Linux systems maintenance and security patch management.',
    'position_requirements': '[Roles & Responsibilities]\n• Installing, configuring, managing and troubleshooting Server and Storage (Virtualized and Hardware).\n• Systems administration and monitoring infrastructure.\n• Participate in the design of information and operational support systems.\n• Evaluate and apply necessary operating system security patches, hotfixes, service packs, and hardware updates.\n• Provide level 1 support, and escalate to level 2 if needed.\n\n[Qualifications & Requirements]\n• Bachelor\'s degree or 4th-year student in Computer Science.\n• Basic knowledge of server hardware and networking.\n• Hands-on experience working with VMware vSphere and vCenter.\n• Clear understanding of Active Directory and DNS concepts with Windows Server 2016/2022.\n• Practical experience in installing, configuring, and troubleshooting UNIX/Linux environments.\n• Good team player with strong communication skills and ability to work under pressure.',
    'jd_file_name': 'recruitment/requisition_jds/Job_Description_System_Specialist.docx',
    'hr_reviewer': 'Sin Thida',
    'hr_reviewed_date': '14.10.26',
    'approved_by': 'KHIEU Sarvorneat',
    'approved_date': '14.10.26',
    'status': 'approved'
}

html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Staff Requisition Form - {data['requisition_code']}</title>
    <style>
        @page {{
            size: letter portrait;
            margin-top: 0.35in;
            margin-bottom: 0.30in;
            margin-left: 0.45in;
            margin-right: 0.45in;
        }}
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 7.8pt;
            color: #000000;
            line-height: 1.25;
            margin: 0;
            padding: 0;
        }}
        table, tr, td, th {{
            border: 0px solid transparent;
            padding: 0;
            margin: 0;
        }}
        /* Main Container Border */
        .doc-frame {{
            border: 1.25pt solid #000000;
            width: 100%;
        }}
        /* Gray Section Banners - Arial Bold 7.8pt, background #D0CECE */
        .banner {{
            background-color: #D0CECE;
            border-top: 0.75pt solid #000000;
            border-bottom: 0.75pt solid #000000;
            text-align: center;
            font-weight: bold;
            font-size: 7.8pt;
            padding: 3pt 0;
            color: #000000;
        }}
        .title-banner {{
            background-color: #D0CECE;
            border-top: 1pt solid #000000;
            border-bottom: 1pt solid #000000;
            text-align: center;
            font-weight: bold;
            font-size: 9.96pt;
            padding: 4pt 0;
            color: #000000;
        }}
        /* Column Tables with exact vertical dividers */
        .col-table th {{
            border-bottom: 0.75pt solid #000000;
            border-right: 0.75pt solid #000000;
            padding: 3.5pt 5pt;
            font-size: 7.8pt;
            font-weight: bold;
            text-align: left;
            height: 15pt;
            background-color: #ffffff;
            color: #000000;
        }}
        .col-table td {{
            border-bottom: 0.75pt solid #000000;
            border-right: 0.75pt solid #000000;
            padding: 3.5pt 5pt;
            font-size: 7.8pt;
            font-weight: normal;
            height: 18pt;
            vertical-align: middle;
            color: #000000;
        }}
        /* Employment Status section uses Calibri */
        .emp-status-container {{
            font-family: Calibri, Arial, sans-serif;
            font-size: 7.85pt;
            padding: 8pt 10pt;
            border-bottom: 0.75pt solid #000000;
            color: #000000;
        }}
        /* Boxed input fields inside Employment Status */
        .box-field {{
            border: 0.75pt solid #000000;
            height: 13pt;
            line-height: 13pt;
            padding: 0 4pt;
            font-size: 7.85pt;
            font-weight: bold;
            background-color: #ffffff;
        }}
        /* Full Time / Part Time Framed Box */
        .blue-subbox {{
            border: 0.75pt solid #41719c;
            width: 98%;
            margin-top: 4pt;
            margin-bottom: 5pt;
        }}
        /* Scalable Content Areas for Justification & Position Requirements */
        .scalable-section {{
            padding: 6pt 8pt;
            font-size: 7.8pt;
            line-height: 1.35;
            color: #000000;
        }}
        /* Approvals Box (Unified Table with 1.25pt border) */
        .approvals-table {{
            border: 1.25pt solid #000000;
            width: 100%;
            margin-top: 8pt;
            font-family: Calibri, Arial, sans-serif;
        }}
        .approvals-banner {{
            background-color: #D0CECE;
            border-bottom: 0.75pt solid #000000;
            text-align: center;
            font-weight: bold;
            font-size: 8.52pt;
            padding: 3.5pt 0;
            color: #000000;
        }}
        .req-asterisk {{
            color: #ff0000;
            font-weight: normal;
        }}
    </style>
</head>
<body>

    <!-- Outer Form Frame -->
    <div class="doc-frame">
        
        <!-- Header: Logo on left, Ticket Code on right -->
        <table style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <td style="padding: 6pt 10pt; width: 65%; vertical-align: middle;">
                    <img src="data:image/jpeg;base64,{logo_b64}" width="125" />
                </td>
                <td style="padding: 6pt 10pt; width: 35%; text-align: right; vertical-align: top;">
                    <div style="font-size: 7pt; color: #555555;">Requisition Code:</div>
                    <div style="font-size: 9pt; font-weight: bold; color: #111111;">{data['requisition_code']}</div>
                </td>
            </tr>
        </table>

        <!-- Title Banner -->
        <div class="title-banner">
            Staff Requisition Form
        </div>

        <!-- Note Section -->
        <div style="padding: 6pt 8pt; border-bottom: 0.75pt solid #000000; font-size: 7.8pt;">
            <strong style="font-size: 7.8pt;">Note:</strong><br><br>
            All fields are mandatory; requisition will be considered only if this form is fully completed.
        </div>

        <!-- Position Details Banner -->
        <div class="banner">
            Position Details
        </div>

        <!-- Position Details Table (Exact 4 Column Bars) -->
        <table class="col-table" style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <th style="width: 38.2%;"><span class="req-asterisk">*</span> Position to be requested</th>
                <th style="width: 18.0%;"><span class="req-asterisk">*</span> Based Location</th>
                <th style="width: 17.2%;"><span class="req-asterisk">*</span> Function</th>
                <th style="width: 26.6%; border-right: none;"><span class="req-asterisk">*</span> Department</th>
            </tr>
            <tr>
                <td><strong>{data['position_title']}</strong></td>
                <td>{data['location']}</td>
                <td>{data['function']}</td>
                <td style="border-right: none;"><strong>{data['department']}</strong></td>
            </tr>
        </table>

        <!-- Line Manager's Details Banner -->
        <div class="banner" style="border-top: none;">
            Line Manager's Details
        </div>

        <!-- Line Manager's Details Table (Exact 2 Column Bars) -->
        <table class="col-table" style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <th style="width: 56.2%;"><span class="req-asterisk">*</span> Manager's Name</th>
                <th style="width: 43.8%; border-right: none;">Position</th>
            </tr>
            <tr>
                <td><strong>{data['manager_name']}</strong></td>
                <td style="border-right: none;">{data['manager_position']}</td>
            </tr>
        </table>

        <!-- Employment Status Banner -->
        <div class="banner" style="border-top: none;">
            Employment Status
        </div>

        <!-- Employment Status Content -->
        <div class="emp-status-container">
            
            <!-- Row 1: PERMANENT & Target Onboarding Date / Level -->
            <table style="width: 100%;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 56%; vertical-align: top;">
                        <table cellspacing="0" cellpadding="0" style="margin-bottom: 5pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['employment_type'] == 'permanent' else chk_empty}</td>
                                <td style="vertical-align: middle;"><strong style="font-size: 7.82pt;">PERMANENT</strong></td>
                            </tr>
                        </table>

                        <table cellspacing="0" cellpadding="0" style="margin-left: 14pt; margin-bottom: 4pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['permanent_category'] == 'budgeted' else chk_empty}</td>
                                <td style="vertical-align: middle; font-size: 7.85pt;">Additional Headcount Budgetted</td>
                            </tr>
                        </table>

                        <table cellspacing="0" cellpadding="0" style="margin-left: 14pt; margin-bottom: 4pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['permanent_category'] == 'non_budgeted' else chk_empty}</td>
                                <td style="vertical-align: middle; font-size: 7.85pt;">Additional Headcount - Non-Budgetted</td>
                            </tr>
                        </table>
                    </td>

                    <td style="width: 44%; vertical-align: top; padding-left: 10pt;">
                        <table style="width: 100%;" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 55%; vertical-align: middle; font-size: 8.52pt;">Target onboarding date:</td>
                                <td style="width: 45%;"><div class="box-field" style="text-align: center;">{data['target_onboarding_date']}</div></td>
                            </tr>
                            <tr>
                                <td style="vertical-align: middle; padding-top: 5pt; font-size: 7.85pt;">Position Level:</td>
                                <td style="padding-top: 5pt;"><div class="box-field" style="text-align: center;">{data['position_level']}</div></td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Replacement for & Reason(s) -->
            <table style="width: 100%; margin-top: 3pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 14pt; vertical-align: middle; padding-left: 14pt;">
                        {chk_checked if data['permanent_category'] == 'replacement' else chk_empty}
                    </td>
                    <td style="width: 90pt; vertical-align: middle; font-size: 7.82pt;">
                        Replacement for
                    </td>
                    <td style="padding-right: 5pt;">
                        <div class="box-field">{data['replacement_for']}</div>
                    </td>
                </tr>
                <tr>
                    <td></td>
                    <td style="vertical-align: middle; padding-top: 4pt; padding-left: 14pt; font-size: 7.85pt;">
                        Reason(s):
                    </td>
                    <td style="padding-right: 5pt; padding-top: 4pt;">
                        <div class="box-field">{data['replacement_reason']}</div>
                    </td>
                </tr>
            </table>

            <!-- Contract & INTERN Row -->
            <table style="width: 100%; margin-top: 8pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 25%; vertical-align: middle;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['employment_type'] == 'contract' else chk_empty}</td>
                                <td style="vertical-align: middle;"><strong style="font-size: 7.85pt;">Contract</strong></td>
                            </tr>
                        </table>
                    </td>
                    <td style="width: 75%; vertical-align: middle;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['employment_type'] == 'intern' else chk_empty}</td>
                                <td style="vertical-align: middle;"><strong style="font-size: 7.85pt;">INTERN</strong></td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Full Time / Part Time Sub-Box (Only this has thin blue border) -->
            <table class="blue-subbox" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="padding: 3pt 10pt; width: 35%;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['contract_term'] == 'full_time' else chk_empty}</td>
                                <td style="vertical-align: middle; font-size: 7.85pt;">Full Time</td>
                            </tr>
                        </table>
                    </td>
                    <td style="padding: 3pt 10pt; width: 65%;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked if data['contract_term'] == 'part_time' else chk_empty}</td>
                                <td style="vertical-align: middle; font-size: 7.85pt;">Part Time</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Employment Period -->
            <table style="width: 100%; margin-top: 4pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 110pt; vertical-align: middle; font-size: 7.82pt;">Employment Period from:</td>
                    <td style="width: 135pt;"><div class="box-field" style="text-align: center;">{data['period_from']}</div></td>
                    <td style="width: 25pt; text-align: center; vertical-align: middle; font-size: 7.85pt;">To:</td>
                    <td style="width: 135pt;"><div class="box-field" style="text-align: center;">{data['period_to']}</div></td>
                    <td></td>
                </tr>
            </table>

            <!-- Working Day & Hour -->
            <table style="width: 100%; margin-top: 5pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 110pt; vertical-align: middle; font-size: 7.85pt;">Working Day & Hour:</td>
                    <td style="width: 300pt;"><div class="box-field">{data['working_days_hours']}</div></td>
                    <td></td>
                </tr>
            </table>

        </div>

        <!-- Section 4: Justification (SCALES VERTICALLY / CAN FLOW DOWN) -->
        <div class="banner" style="border-top: none;">
            Justification (Why is this position needed?)
        </div>
        <div class="scalable-section" style="border-bottom: 0.75pt solid #000000; min-height: 38pt;">
            {data['justification'].replace(chr(10), '<br>')}
        </div>

        <!-- Section 5: Position Requirements (SCALES VERTICALLY / CAN FLOW DOWN) -->
        <div class="banner" style="border-top: none;">
            Position Requirements (refer to JD attached)
        </div>
        <div class="scalable-section" style="min-height: 48pt;">
            {data['position_requirements'].replace(chr(10), '<br>')}
            <div style="margin-top: 5pt; color: #555555; font-size: 7pt;">
                (Job Description attached: {data['jd_file_name']})
            </div>
        </div>

    </div>

    <!-- Section 6: Approvals (Single unified cell so banner + 3 signature columns stay together) -->
    <table class="approvals-table" cellspacing="0" cellpadding="0">
        <tr>
            <td style="padding: 0;">
                <div class="approvals-banner">
                    Approvals
                </div>
                <table style="width: 100%;" cellspacing="0" cellpadding="0">
                    <tr>
                        <td style="width: 33.3%; padding: 8pt 14pt; vertical-align: top; font-size: 8.52pt;">
                            <strong>Requested by (hiring manager)</strong>
                            <div style="height: 35pt; padding-top: 8pt; font-style: italic;">
                                {data['manager_name']}
                            </div>
                            <div>Date: &nbsp; {data['requested_date']}</div>
                        </td>
                        <td style="width: 33.3%; padding: 8pt 14pt; vertical-align: top; font-size: 8.52pt;">
                            <strong>Checked HR Rep</strong>
                            <div style="height: 35pt; padding-top: 8pt; font-style: italic;">
                                {data['hr_reviewer']}
                            </div>
                            <div>Date: &nbsp; {data['hr_reviewed_date']}</div>
                        </td>
                        <td style="width: 33.4%; padding: 8pt 14pt; vertical-align: top; font-size: 8.52pt;">
                            <strong>Approved by CEO</strong>
                            <div style="height: 35pt; padding-top: 8pt; font-style: italic;">
                                {data['approved_by']}
                            </div>
                            <div>Date: &nbsp; {data['approved_date']}</div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    <!-- Quality Form Footer -->
    <table style="width: 100%; margin-top: 4pt; font-family: Calibri, Arial, sans-serif;" cellspacing="0" cellpadding="0">
        <tr>
            <td style="width: 50%;"></td>
            <td style="width: 50%; text-align: right; font-size: 7.80pt; line-height: 1.2; color: #000000;">
                RMO-HRA-QF-001<br>
                Revision 001<br>
                01.06.24
            </td>
        </tr>
    </table>

</body>
</html>'''

out = BytesIO()
pisa_status = pisa.CreatePDF(html, dest=out)
pdf_data = out.getvalue()
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/test_exact_scaling.pdf', 'wb') as f:
    f.write(pdf_data)

doc = fitz.open(stream=pdf_data, filetype='pdf')
print('PAGES IN EXACT SCALING PDF:', len(doc))
