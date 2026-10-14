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

chk_empty_html = f'<img src="data:image/png;base64,{empty_b64}" width="10" height="7" />'
chk_checked_html = f'<img src="data:image/png;base64,{checked_b64}" width="10" height="7" />'

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

html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Staff Requisition Form - {data['requisition_code']}</title>
    <style>
        @page {{
            size: letter portrait;
            margin-top: 0.35in;
            margin-bottom: 0.30in;
            margin-left: 0.50in;
            margin-right: 0.50in;
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            font-size: 8pt;
            color: #000;
            line-height: 1.25;
            margin: 0;
            padding: 0;
        }}
        .main-frame {{
            border: 1.5pt solid #000;
            width: 100%;
        }}
        .banner {{
            background-color: #D0CECE;
            border-top: 1pt solid #000;
            border-bottom: 1pt solid #000;
            text-align: center;
            font-weight: bold;
            font-size: 8pt;
            padding: 3.5pt 0;
        }}
        .title-banner {{
            background-color: #D0CECE;
            border-top: 1.5pt solid #000;
            border-bottom: 1pt solid #000;
            text-align: center;
            font-weight: bold;
            font-size: 10pt;
            padding: 4pt 0;
        }}
        .grid-table {{
            width: 100%;
        }}
        .grid-table th, .grid-table td {{
            border-top: 0.75pt solid #000;
            border-bottom: 0.75pt solid #000;
            border-right: 0.75pt solid #000;
            padding: 3.5pt 6pt;
            font-size: 7.8pt;
            vertical-align: middle;
        }}
        .grid-table th {{
            font-weight: normal;
            text-align: left;
            background-color: #fff;
            height: 15pt;
        }}
        .val-cell {{
            font-weight: bold;
            font-size: 8pt;
            height: 18pt;
        }}
        .input-cell {{
            border: 0.75pt solid #000;
            background-color: #ffffff;
            height: 14pt;
            line-height: 14pt;
            padding: 0 4pt;
            font-size: 7.8pt;
            font-weight: bold;
        }}
        .approvals-frame {{
            border: 1.5pt solid #000;
            width: 100%;
            margin-top: 8pt;
        }}
        /* Scalable content sections */
        .scalable-box {{
            padding: 6pt 8pt;
            font-size: 7.8pt;
            line-height: 1.35;
            min-height: 35pt;
        }}
    </style>
</head>
<body>

    <!-- Main Upper Form Container -->
    <div class="main-frame">
        
        <!-- Top Header: Logo on left, Ticket Code on right (NO vertical border) -->
        <table style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <td style="padding: 6pt 10pt; width: 60%; vertical-align: middle;">
                    <img src="data:image/jpeg;base64,{logo_b64}" width="125" />
                </td>
                <td style="padding: 6pt 10pt; width: 40%; text-align: right; vertical-align: top;">
                    <div style="font-size: 7.5pt; color: #555;">Requisition Code:</div>
                    <div style="font-size: 9.5pt; font-weight: bold; color: #111;">{data['requisition_code']}</div>
                </td>
            </tr>
        </table>

        <!-- Title Banner -->
        <div class="title-banner">
            Staff Requisition Form
        </div>

        <!-- Note Section -->
        <div style="padding: 5pt 8pt; border-bottom: 1pt solid #000; font-size: 7.8pt;">
            <strong>Note:</strong><br><br>
            All fields are mandatory; requisition will be considered only if this form is fully completed.
        </div>

        <!-- Section 1: Position Details -->
        <div class="banner">
            Position Details
        </div>
        <table class="grid-table" cellspacing="0" cellpadding="0">
            <tr>
                <th style="width: 38.2%;">* Position to be requested</th>
                <th style="width: 18.0%;">* Based Location</th>
                <th style="width: 17.2%;">* Function</th>
                <th style="width: 26.6%; border-right: none;">* Department</th>
            </tr>
            <tr>
                <td class="val-cell">{data['position_title']}</td>
                <td class="val-cell">{data['location']}</td>
                <td class="val-cell">{data['function']}</td>
                <td class="val-cell" style="border-right: none;">{data['department']}</td>
            </tr>
        </table>

        <!-- Section 2: Line Manager's Details -->
        <div class="banner" style="border-top: none;">
            Line Manager's Details
        </div>
        <table class="grid-table" cellspacing="0" cellpadding="0">
            <tr>
                <th style="width: 56.2%;">* Manager's Name</th>
                <th style="width: 43.8%; border-right: none;">Position</th>
            </tr>
            <tr>
                <td class="val-cell">{data['manager_name']}</td>
                <td class="val-cell" style="border-right: none;">{data['manager_position']}</td>
            </tr>
        </table>

        <!-- Section 3: Employment Status -->
        <div class="banner" style="border-top: none;">
            Employment Status
        </div>
        
        <div style="padding: 8pt 10pt; border-bottom: 1pt solid #000; font-size: 7.8pt;">
            
            <!-- Row 1: PERMANENT + TARGET ONBOARDING DATE & POSITION LEVEL -->
            <table style="width: 100%;" cellspacing="0" cellpadding="0">
                <tr>
                    <!-- Permanent column -->
                    <td style="width: 58%; vertical-align: top;">
                        <table cellspacing="0" cellpadding="0" style="margin-bottom: 5pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['employment_type'] == 'permanent' else chk_empty_html}</td>
                                <td style="vertical-align: middle;"><strong style="font-size: 8pt;">PERMANENT</strong></td>
                            </tr>
                        </table>
                        <table cellspacing="0" cellpadding="0" style="margin-left: 18pt; margin-bottom: 5pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['permanent_category'] == 'budgeted' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Additional Headcount Budgetted</td>
                            </tr>
                        </table>
                        <table cellspacing="0" cellpadding="0" style="margin-left: 18pt; margin-bottom: 5pt;">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['permanent_category'] == 'non_budgeted' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Additional Headcount - Non-Budgetted</td>
                            </tr>
                        </table>
                    </td>

                    <!-- Right Column: Target onboarding date & Position Level -->
                    <td style="width: 42%; vertical-align: top; padding-left: 5pt;">
                        <table style="width: 100%;" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 58%; vertical-align: middle;">Target onboarding date:</td>
                                <td style="width: 42%;"><div class="input-cell" style="text-align: center;">{data['target_onboarding_date']}</div></td>
                            </tr>
                            <tr>
                                <td style="vertical-align: middle; padding-top: 6pt;">Position Level:</td>
                                <td style="padding-top: 6pt;"><div class="input-cell" style="text-align: center;">{data['position_level']}</div></td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Replacement for & Reason(s) Rows (aligned to master grid) -->
            <table style="width: 100%; margin-top: 3pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 18pt; vertical-align: middle;">
                        {chk_checked_html if data['permanent_category'] == 'replacement' else chk_empty_html}
                    </td>
                    <td style="width: 100pt; vertical-align: middle;">
                        Replacement for
                    </td>
                    <td style="padding-left: 2pt;">
                        <div class="input-cell">{data['replacement_for']}</div>
                    </td>
                </tr>
                <tr>
                    <td></td>
                    <td style="vertical-align: middle; padding-top: 4pt;">
                        Reason(s):
                    </td>
                    <td style="padding-left: 2pt; padding-top: 4pt;">
                        <div class="input-cell">{data['replacement_reason']}</div>
                    </td>
                </tr>
            </table>

            <!-- Row 2: CONTRACT / INTERN -->
            <table style="width: 100%; margin-top: 8pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 25%; vertical-align: middle;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['employment_type'] == 'contract' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Contract</td>
                            </tr>
                        </table>
                    </td>
                    <td style="width: 75%; vertical-align: middle;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['employment_type'] == 'intern' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">INTERN</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Full Time / Part Time Sub-Box (Bordered in blue) -->
            <table style="width: 98%; border: 0.75pt solid #41719c; margin-top: 4pt; margin-bottom: 5pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="padding: 3.5pt 10pt; width: 35%;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['contract_term'] == 'full_time' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Full Time</td>
                            </tr>
                        </table>
                    </td>
                    <td style="padding: 3.5pt 10pt; width: 65%;">
                        <table cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="width: 14pt; vertical-align: middle;">{chk_checked_html if data['contract_term'] == 'part_time' else chk_empty_html}</td>
                                <td style="vertical-align: middle;">Part Time</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Employment Period From / To -->
            <table style="width: 100%; margin-top: 4pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 118pt; vertical-align: middle;">Employment Period from:</td>
                    <td style="width: 140pt;"><div class="input-cell" style="text-align: center;">{data['period_from']}</div></td>
                    <td style="width: 30pt; text-align: center; vertical-align: middle;">To:</td>
                    <td style="width: 140pt;"><div class="input-cell" style="text-align: center;">{data['period_to']}</div></td>
                    <td></td>
                </tr>
            </table>

            <!-- Working Day & Hour -->
            <table style="width: 100%; margin-top: 5pt;" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="width: 118pt; vertical-align: middle;">Working Day & Hour:</td>
                    <td style="width: 310pt;"><div class="input-cell">{data['working_days_hours']}</div></td>
                    <td></td>
                </tr>
            </table>

        </div>

        <!-- Section 4: Justification (SCALES VERTICALLY) -->
        <div class="banner" style="border-top: none;">
            Justification (Why is this position needed?)
        </div>
        <div class="scalable-box" style="border-bottom: 1pt solid #000;">
            {data['justification'].replace(chr(10), '<br>')}
        </div>

        <!-- Section 5: Position Requirements (SCALES VERTICALLY) -->
        <div class="banner" style="border-top: none;">
            Position Requirements (refer to JD attached)
        </div>
        <div class="scalable-box">
            {data['position_requirements'].replace(chr(10), '<br>')}
            <div style="margin-top: 6pt; color: #555; font-size: 7.2pt;">
                (Job Description attached: {data['jd_file_name']})
            </div>
        </div>

    </div>

    <!-- Section 6: Approvals (Fixed 3-Column Hierarchy) -->
    <div class="approvals-frame">
        <div class="banner" style="border-top: none;">
            Approvals
        </div>
        <table style="width: 100%;" cellspacing="0" cellpadding="0">
            <tr>
                <td style="width: 33.3%; padding: 8pt 14pt; vertical-align: top; font-size: 7.8pt;">
                    <strong>Requested by (hiring manager)</strong>
                    <div style="height: 35pt; padding-top: 8pt; font-style: italic;">
                        {data['manager_name']}
                    </div>
                    <div>Date: &nbsp; {data['requested_date']}</div>
                </td>
                <td style="width: 33.3%; padding: 8pt 14pt; vertical-align: top; font-size: 7.8pt;">
                    <strong>Checked HR Rep</strong>
                    <div style="height: 35pt; padding-top: 8pt; font-style: italic;">
                        {data['hr_reviewer']}
                    </div>
                    <div>Date: &nbsp; {data['hr_reviewed_date']}</div>
                </td>
                <td style="width: 33.4%; padding: 8pt 14pt; vertical-align: top; font-size: 7.8pt;">
                    <strong>Approved by CEO</strong>
                    <div style="height: 35pt; padding-top: 8pt; font-style: italic;">
                        {data['approved_by']}
                    </div>
                    <div>Date: &nbsp; {data['approved_date']}</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Official Quality Code Footer -->
    <table style="width: 100%; margin-top: 4pt;" cellspacing="0" cellpadding="0">
        <tr>
            <td style="width: 50%;"></td>
            <td style="width: 50%; text-align: right; font-size: 7pt; line-height: 1.2; color: #000;">
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
print('PDF error status:', pisa_status.err)
pdf_data = out.getvalue()
with open('C:/Users/Chanheng Menh/Documents/horilla-hrms/scratch/test_rmo_robust.pdf', 'wb') as f:
    f.write(pdf_data)

doc = fitz.open(stream=pdf_data, filetype='pdf')
print('PAGES IN ROBUST RMO PDF:', len(doc))
