import base64
import os
from io import BytesIO
from xhtml2pdf import pisa

with open('scratch/extracted_img_7_Image30.jpg', 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode('utf-8')

# Sample dummy data for System Specialist
data = {
    'requisition_code': 'REQ-2026-0013',
    'position_title': 'System Specialist',
    'location': 'RMO Technology Main Office',
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
    'justification': 'Support Server & Storage configuration, ensure 24/7 service operation stability for enterprise customer infrastructure expansion.',
    'position_requirements': 'Bachelor in Computer Science or IT; 3+ years experience with Windows/Linux Servers, VMware virtualization, SAN storage configuration, and backup solutions.',
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
            margin-top: 0.45in;
            margin-bottom: 0.35in;
            margin-left: 0.55in;
            margin-right: 0.55in;
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
            border: 1.5px solid #000;
            width: 100%;
            margin-bottom: 9px;
        }}
        .banner {{
            background-color: #D0CECE;
            border-top: 1px solid #000;
            border-bottom: 1px solid #000;
            text-align: center;
            font-weight: bold;
            font-size: 8.5pt;
            padding: 3px 0;
        }}
        .title-banner {{
            background-color: #D0CECE;
            border-top: 1.5px solid #000;
            border-bottom: 1px solid #000;
            text-align: center;
            font-weight: bold;
            font-size: 10pt;
            padding: 4px 0;
        }}
        .table-grid {{
            width: 100%;
            border-collapse: collapse;
        }}
        .table-grid th, .table-grid td {{
            border: 1px solid #000;
            padding: 4px 6px;
            font-size: 7.8pt;
            vertical-align: middle;
        }}
        .table-grid th {{
            font-weight: normal;
            text-align: left;
            background-color: #fff;
        }}
        .val-cell {{
            font-weight: bold;
            min-height: 20px;
            font-size: 8pt;
        }}
        .chk-empty {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border: 1px solid #000;
            margin-right: 4px;
            vertical-align: middle;
        }}
        .chk-checked {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border: 1px solid #000;
            margin-right: 4px;
            vertical-align: middle;
            text-align: center;
            line-height: 7px;
            font-size: 7.5pt;
            font-weight: bold;
        }}
        .input-box {{
            display: inline-block;
            border: 1px solid #000;
            height: 14px;
            line-height: 14px;
            padding: 0 4px;
            font-weight: bold;
            font-size: 7.8pt;
            vertical-align: middle;
        }}
        .approvals-frame {{
            border: 1.5px solid #000;
            width: 100%;
        }}
        .footer-table {{
            width: 100%;
            margin-top: 4px;
        }}
        .footer-text {{
            text-align: right;
            font-size: 7.5pt;
            line-height: 1.2;
            color: #000;
        }}
    </style>
</head>
<body>

    <!-- Main Upper Frame -->
    <div class="main-frame">
        
        <!-- Header Logo Area -->
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 6px 10px; width: 50%;">
                    <img src="data:image/jpeg;base64,{logo_b64}" width="125" />
                </td>
                <td style="padding: 6px 10px; width: 50%; text-align: right; vertical-align: top;">
                    <span style="font-size: 7.8pt; color: #555;">Requisition Code:</span><br>
                    <strong style="font-size: 9.5pt; color: #111;">{data['requisition_code']}</strong>
                </td>
            </tr>
        </table>

        <!-- Title Banner -->
        <div class="title-banner">
            Staff Requisition Form
        </div>

        <!-- Note Section -->
        <div style="padding: 6px 8px; border-bottom: 1px solid #000; font-size: 7.8pt;">
            <strong>Note:</strong><br><br>
            All fields are mandatory; requisition will be considered only if this form is fully completed.
        </div>

        <!-- Position Details Banner -->
        <div class="banner">
            Position Details
        </div>

        <!-- Position Details Table -->
        <table class="table-grid" style="border-left: none; border-right: none;">
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
        <table class="table-grid" style="border-left: none; border-right: none;">
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
        <div style="padding: 8px 10px; border-bottom: 1px solid #000; font-size: 7.8pt;">
            
            <!-- PERMANENT ROW -->
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 6px;">
                <tr>
                    <td style="width: 55%; vertical-align: top;">
                        <span class="{'chk-checked' if data['employment_type'] == 'permanent' else 'chk-empty'}">{'X' if data['employment_type'] == 'permanent' else '&nbsp;'}</span>
                        <strong>PERMANENT</strong>
                        
                        <div style="margin-left: 18px; margin-top: 5px;">
                            <span class="{'chk-checked' if data['permanent_category'] == 'budgeted' else 'chk-empty'}">{'X' if data['permanent_category'] == 'budgeted' else '&nbsp;'}</span>
                            Additional Headcount Budgetted
                        </div>
                        <div style="margin-left: 18px; margin-top: 5px;">
                            <span class="{'chk-checked' if data['permanent_category'] == 'non_budgeted' else 'chk-empty'}">{'X' if data['permanent_category'] == 'non_budgeted' else '&nbsp;'}</span>
                            Additional Headcount - Non-Budgetted
                        </div>
                        <div style="margin-left: 18px; margin-top: 5px;">
                            <span class="{'chk-checked' if data['permanent_category'] == 'replacement' else 'chk-empty'}">{'X' if data['permanent_category'] == 'replacement' else '&nbsp;'}</span>
                            Replacement for: &nbsp;
                            <span class="input-box" style="width: 140px;">{data['replacement_for']}</span>
                        </div>
                        <div style="margin-left: 18px; margin-top: 5px;">
                            Reason(s): &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                            <span class="input-box" style="width: 140px;">{data['replacement_reason']}</span>
                        </div>
                    </td>
                    <td style="width: 45%; vertical-align: top; padding-left: 10px;">
                        <div style="margin-top: 15px;">
                            Target onboarding date: &nbsp;
                            <span class="input-box" style="width: 75px;">{data['target_onboarding_date']}</span>
                        </div>
                        <div style="margin-top: 8px;">
                            Position Level: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                            <span class="input-box" style="width: 75px;">{data['position_level']}</span>
                        </div>
                    </td>
                </tr>
            </table>

            <!-- CONTRACT / INTERN ROW -->
            <table style="width: 100%; border-collapse: collapse; margin-top: 4px;">
                <tr>
                    <td style="width: 25%;">
                        <span class="{'chk-checked' if data['employment_type'] == 'contract' else 'chk-empty'}">{'X' if data['employment_type'] == 'contract' else '&nbsp;'}</span>
                        Contract
                    </td>
                    <td style="width: 75%;">
                        <span class="{'chk-checked' if data['employment_type'] == 'intern' else 'chk-empty'}">{'X' if data['employment_type'] == 'intern' else '&nbsp;'}</span>
                        INTERN
                    </td>
                </tr>
            </table>

            <!-- FULL TIME / PART TIME SUB-BOX -->
            <table style="width: 95%; border: 1px solid #41719c; margin-top: 5px; margin-bottom: 5px;">
                <tr>
                    <td style="padding: 3px 8px; width: 30%;">
                        <span class="{'chk-checked' if data['contract_term'] == 'full_time' else 'chk-empty'}">{'X' if data['contract_term'] == 'full_time' else '&nbsp;'}</span>
                        Full Time
                    </td>
                    <td style="padding: 3px 8px; width: 70%;">
                        <span class="{'chk-checked' if data['contract_term'] == 'part_time' else 'chk-empty'}">{'X' if data['contract_term'] == 'part_time' else '&nbsp;'}</span>
                        Part Time
                    </td>
                </tr>
            </table>

            <!-- EMPLOYMENT PERIOD -->
            <div style="margin-top: 5px;">
                Employment Period from: &nbsp;
                <span class="input-box" style="width: 120px;">{data['period_from']}</span>
                &nbsp;&nbsp;&nbsp;&nbsp; To: &nbsp;
                <span class="input-box" style="width: 120px;">{data['period_to']}</span>
            </div>

            <div style="margin-top: 5px;">
                Working Day & Hour: &nbsp;
                <span class="input-box" style="width: 280px;">{data['working_days_hours']}</span>
            </div>

        </div>

        <!-- Justification Banner -->
        <div class="banner" style="border-top: none;">
            Justification (Why is this position needed?)
        </div>
        <div style="padding: 6px 8px; min-height: 38px; border-bottom: 1px solid #000; font-size: 7.8pt;">
            {data['justification']}
        </div>

        <!-- Position Requirements Banner -->
        <div class="banner" style="border-top: none;">
            Position Requirements (refer to JD attached)
        </div>
        <div style="padding: 6px 8px; min-height: 48px; font-size: 7.8pt;">
            {data['position_requirements']}
        </div>

    </div>

    <!-- Approvals Frame -->
    <div class="approvals-frame">
        <div class="banner" style="border-top: none;">
            Approvals
        </div>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="width: 33.3%; padding: 8px 12px; vertical-align: top; font-size: 7.8pt;">
                    <strong>Requested by (hiring manager)</strong>
                    <div style="height: 32px; padding-top: 10px; font-style: italic;">
                        {data['manager_name']}
                    </div>
                    <div>Date: &nbsp; {data['requested_date']}</div>
                </td>
                <td style="width: 33.3%; padding: 8px 12px; vertical-align: top; font-size: 7.8pt;">
                    <strong>Checked HR Rep</strong>
                    <div style="height: 32px; padding-top: 10px; font-style: italic;">
                        {data['hr_reviewer']}
                    </div>
                    <div>Date: &nbsp; {data['hr_reviewed_date']}</div>
                </td>
                <td style="width: 33.4%; padding: 8px 12px; vertical-align: top; font-size: 7.8pt;">
                    <strong>Approved by CEO</strong>
                    <div style="height: 32px; padding-top: 10px; font-style: italic;">
                        {data['approved_by']}
                    </div>
                    <div>Date: &nbsp; {data['approved_date']}</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Footer -->
    <table class="footer-table">
        <tr>
            <td style="width: 50%;"></td>
            <td style="width: 50%;" class="footer-text">
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
print('PDF byte length:', len(out.getvalue()))
with open('scratch/test_rmo_rendered.pdf', 'wb') as f:
    f.write(out.getvalue())
