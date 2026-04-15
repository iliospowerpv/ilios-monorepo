"""Generate a comprehensive synthetic Site Lease PDF for Desert Bloom Solar + Storage."""
from fpdf import FPDF
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "Desert_Bloom_Site_Lease_Agreement.pdf")


class LeasePDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, title)
        self.ln(3)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def indent_body(self, text, indent=10):
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0 - indent, 5, text)
        self.ln(2)

    def cover_field(self, label, value, lw=45):
        self.set_font("Helvetica", "B", 10)
        self.cell(lw, 6, label, ln=False)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, value)


pdf = LeasePDF()
pdf.set_auto_page_break(auto=True, margin=20)

# ======== COVER SHEET ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 8, "GROUND LEASE AGREEMENT FOR SOLAR PROJECT", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "COVER SHEET", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)

cover_fields = [
    ("Owner:", "Mojave Solar Ranch LLC, a California limited liability company"),
    ("Tenant:", "Desert Bloom Solar LLC, a Delaware limited liability company"),
    ("Property\nAddress:", "12500 Mojave Desert Highway, Barstow, CA 92311\nSan Bernardino County, California"),
    ("Effective Date:", "June 15, 2023"),
    ("End of\nFeasibility\nPeriod:", "December 15, 2023 (Six months from Effective Date)"),
    ("Commencement\nDate:", "To be the date of the notice to proceed described in Section 2 of the Lease."),
    ("Base Rent:", "$185,000.00 annually, payable in equal monthly installments"),
    ("Rent Escalation:", "Two percent (2.0%) per annum, commencing on the first anniversary of the Commencement Date, escalating on June 15 of each Lease Year"),
    ("Deposit:", "$50,000.00 and other valuable consideration"),
    ("Initial Term:", "Commencement Date until 300 months (25 years) from Commercial Operation Date"),
    ("Date of End of\nInitial Term:", "Twenty-five (25) years from Commercial Operation Date"),
    ("Date to Notify\nof Intent to\nExtend:", "Not less than twelve (12) months prior to expiration of Initial Term"),
    ("Renewal Terms:", "Two (2) additional five (5) year terms, at Tenant's election"),
    ("Acreage:", "Approximately four hundred eighty (480) acres"),
    ("Project\nDescription:", "75 MW AC / 98.5 MW DC photovoltaic solar energy generation system with 15.6 MWh / 7.6 MW battery energy storage system (Tesla Megapack 2XL)"),
    ("Owner Address\nfor Notice:", "Mojave Solar Ranch LLC\n45200 National Trails Highway\nNewberry Springs, CA 92365\nAttn: Robert J. Caldwell, Managing Member"),
    ("Tenant Address\nfor Notice:", "Desert Bloom Solar LLC\nc/o Solara Holdings LLC\n100 Solar Innovation Drive\nDenver, CO 80202\nAttn: Victoria Chen, President"),
]

for label, value in cover_fields:
    pdf.cover_field(label, value)
    pdf.ln(1)

pdf.ln(5)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "EXHIBITS:", new_x="LMARGIN", new_y="NEXT")
exhibits = [
    ("Exhibit A:", "Legal Description of Owner's Property"),
    ("Exhibit B:", "Legal Description of Premises (including Easements)"),
    ("Exhibit C:", "Site Plan of Premises, including Solar Facility"),
    ("Exhibit D:", "Form of Memorandum/Notice of Lease"),
    ("Exhibit E:", "Form of Estoppel with Owner's Consent to Finance"),
    ("Exhibit F:", "Form of Easement"),
    ("Exhibit G:", "Form of Estoppel Certificate"),
    ("Exhibit H:", "Rent Schedule"),
    ("Exhibit I:", "Decommissioning Plan and Financial Assurance"),
]
for label, value in exhibits:
    pdf.cover_field(label, value, lw=25)

# ======== PREAMBLE ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 13)
pdf.cell(0, 10, "GROUND LEASE AGREEMENT FOR SOLAR PROJECT", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)

pdf.body(
    'This Ground Lease Agreement For Solar Project (the "Agreement" or "Lease") is made and entered '
    "into as of the Effective Date (as such term is hereinafter defined), by and between Mojave Solar "
    "Ranch LLC, a California limited liability company having a business address of 45200 National "
    'Trails Highway, Newberry Springs, CA 92365 ("Owner"), and Desert Bloom Solar LLC, a Delaware '
    "limited liability company having a business address of 100 Solar Innovation Drive, Denver, CO "
    '80202 ("Tenant"). The Tenant and the Owner are sometimes referred to individually as a "Party" '
    'and collectively as the "Parties."'
)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "Background", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

pdf.body(
    "WHEREAS Owner owns a parcel of real property located in Barstow, San Bernardino County, "
    "California, consisting of approximately four hundred eighty (480) acres of unimproved desert land "
    "situated along the Mojave Desert Highway, as further described in Exhibit A attached hereto and "
    'made part hereof (the "Property");'
)
pdf.body(
    "WHEREAS, Tenant desires to lease from Owner the Property, known as the Premises, as such term "
    "is further defined in Section 1 below, for the purposes of constructing and operating a utility-scale "
    "solar photovoltaic energy generation facility with battery energy storage, as further described in "
    'Section 1 below (the "Project") described herein, and Owner has agreed to lease such Premises to '
    "Tenant for such purpose; and"
)
pdf.body(
    "WHEREAS, the Parties desire to set forth herein the terms and provisions pursuant to which Owner "
    "shall lease the Premises described herein to Tenant, and Tenant shall lease such Premises from "
    "Owner and utilize the same for the purposes set forth herein."
)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "NOW, THEREFORE, IN WITNESS WHEREOF:", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
pdf.body(
    "In consideration of the premises and the mutual covenants and agreements contained herein, "
    "and for other good and valuable consideration, the receipt and sufficiency of which are hereby "
    "acknowledged, and intending to be legally bound, the Parties hereto agree as follows:"
)

# ======== SECTION 1: LEASE OF PREMISES ========
pdf.section_title("Section 1. Lease of Premises.")
pdf.body(
    "Owner hereby demises and leases to Tenant, and Tenant hereby leases from Owner, for the "
    "purposes described herein, including without limitation to develop, design, engineer, construct, "
    "monitor, install, own, operate and maintain the Project, on the Property as further described in "
    "Exhibit B attached hereto and by this reference made a part hereof (together with the Easements, "
    "as such term is hereinafter defined and further described in Exhibit B and Exhibit F, and as the "
    'same may be amended in accordance with the terms hereof, the "Premises"), which Premises are '
    "depicted on the Site Plan that is attached hereto as Exhibit C, and by this reference made a part "
    "hereof, TO HAVE AND TO HOLD the Premises together with all rights, privileges, easements and "
    "appurtenances thereunto belonging and attaching, unto Tenant. This Lease is made upon the "
    "covenants and agreements hereinafter set forth with which the Parties hereto respectively agree "
    "to observe and comply during the Term (as such term is hereinafter defined). The Tenant and "
    "Owner acknowledge that the location and size of the Premises is subject to change pending the "
    "results of Tenant's feasibility studies during the Feasibility Period, as the same is hereinafter "
    "defined. In the event that the Premises must be adjusted or decreased based upon the results of "
    "Tenant's feasibility studies or due to the requirements of local permitting bylaw and rulings, "
    "wetlands, geotechnical investigation, environmental work, Phase I ESA report, utility approvals "
    "and limitations, design configuration, the capacity of the electrical grid, and all other state and "
    "local permits and approvals, in Tenant's sole discretion, then the Owner shall cooperate with "
    "Tenant to amend this Lease prior to the expiration of the Feasibility Period to provide Tenant "
    "with such area as is necessary, in Tenant's reasonable discretion and as a result of any third party "
    "actions, for the installation and operation of a solar photovoltaic generation facility with battery "
    "energy storage, even if such cooperation increases or decreases the area of Owner's retained "
    "possessory interest. The Parties agree to amend this Lease and the Memorandum thereof as "
    "necessary to incorporate a revised description and depiction of the Premises prior to the "
    "Commencement Date, time being of the essence."
)

# ======== SECTION 2: TERM ========
pdf.section_title("Section 2. Term.")
pdf.body(
    'The initial term of this Agreement (the "Initial Term") shall commence on the date on which '
    "Tenant gives any construction contractor a notice to proceed under the appropriate contract to "
    'construct the Project (the "Commencement Date") and shall expire on the twenty-fifth (25th) '
    "anniversary of the date on which the Project begins to sell energy into the grid in commercial "
    'quantities under any power purchase arrangement (the "Commercial Operation Date"), unless '
    "otherwise terminated at an earlier date in accordance with the terms of this Agreement. The "
    "Commencement Date shall be a date prior to the last day of the Feasibility Period, and Tenant "
    "shall provide to Owner thirty (30) days' written notice of such Commencement Date. Provided "
    "Tenant is not in default of the terms of this Lease, Tenant shall have the right to extend this "
    'Lease for two (2) options (each an "Option") for terms of five (5) years each (each a "Renewal '
    'Term"). Tenant shall exercise each Option by giving written notice of its intent to extend the term '
    "of this Lease to Owner not more than twelve (12) months nor less than three (3) months prior to "
    "the expiration of the then current term of the Lease. The term of this Agreement shall be the "
    'Initial Term plus any Renewal Terms (together, the "Term").'
)

# ======== SECTION 3: RENT ========
pdf.section_title("Section 3. Rent.")
pdf.indent_body(
    "(a)    Starting on the Commencement Date until the Commercial Operation Date (the "
    '"Construction Period"), the Tenant shall pay to Owner Ten Thousand Dollars ($10,000.00) '
    "as Construction Period rent per annum, payable in equal monthly installments. In addition, "
    "the Deposit received by Owner pursuant to Section 4 hereof shall be retained by Owner as "
    "consideration for the Feasibility Period and Construction Period rent."
)
pdf.indent_body(
    "(b)    Starting on the Commercial Operation Date, Tenant shall pay to Owner annual rent "
    '("Rent") in the amount of One Hundred Eighty-Five Thousand Dollars ($185,000.00) per '
    'year ("Base Rent"), payable in equal monthly installments of Fifteen Thousand Four '
    "Hundred Sixteen Dollars and Sixty-Seven Cents ($15,416.67), due and payable on the first "
    "(1st) day of each calendar month, in advance. Rent shall be payable by electronic funds "
    "transfer to an account designated by Owner in writing."
)
pdf.indent_body(
    "(c)    The Base Rent shall increase by two percent (2.0%) per annum on each anniversary of "
    "the Commencement Date (June 15 of each Lease Year), commencing on the first (1st) "
    "anniversary of the Commencement Date. The Rent Schedule is attached hereto as Exhibit H "
    "and incorporated by reference."
)
pdf.indent_body(
    "(d)    The Rent for each year of any Renewal Term shall continue to escalate at two percent "
    "(2.0%) per annum as provided in Section 3(c), which Rent shall otherwise be made payable "
    "in accordance with Section 3(b)."
)
pdf.indent_body(
    "(e)    In addition to Base Rent, Tenant shall pay all real property taxes, assessments, and "
    "governmental charges levied against the Premises during the Term (\"Additional Rent\"). "
    "Owner shall forward all tax bills and assessment notices to Tenant within thirty (30) days "
    "of receipt."
)
pdf.indent_body(
    "(f)    If any installment of Rent is not received by Owner within ten (10) days after the date "
    "due, Tenant shall pay a late charge equal to five percent (5%) of the overdue amount, plus "
    "interest on the unpaid amount at the rate of the prime rate published by The Wall Street "
    "Journal plus three percent (3%) per annum from the date due until paid."
)

# ======== SECTION 4: FEASIBILITY ========
pdf.section_title("Section 4. Feasibility and Permitting Period.")
pdf.indent_body(
    "(a)    Owner acknowledges receipt of a non-refundable deposit of Fifty Thousand Dollars "
    '($50,000.00) (the "Deposit") prior to the Effective Date hereof. In consideration for the '
    "Tenant's payment of the Deposit, Tenant and its employees, advisors, representatives, "
    "agents, contractors, and subcontractors, are hereby granted the right for a period "
    "commencing on the Effective Date and terminating six (6) months from the Effective Date "
    '(the "Initial Feasibility Period", and collectively with any extensions thereof pursuant to '
    'Section 4(c) hereof, the "Feasibility Period"), at Tenant\'s sole cost and expense, to enter '
    "upon the Property and conduct such analyses, tests, reviews, inspections and studies "
    '(collectively, the "Tests") as Tenant deems necessary to determine the Property\'s '
    "suitability for Tenant's intended use thereof; to obtain any and all permits, licenses, "
    "agreements and entitlements necessary for Tenant's intended use of the Property; and to "
    "develop, design, engineer, and prepare for construction of the Solar Facility, as the same is "
    "hereinafter defined. Such Tests may include, but are not limited to, surveys, soil, sediment, "
    "surface water and groundwater tests, environmental evaluations, solar resource "
    "assessments, geotechnical investigations, ALTA/NSPS land title surveys, Phase I and "
    "Phase II Environmental Site Assessments, cultural resource surveys, biological resource "
    "surveys, wetland delineations, and such other Tests as Tenant deems necessary or "
    "desirable. In addition, Tenant may obtain an abstract or preliminary title report regarding "
    'the Property from a title insurance company of its choice (the "Title Report").'
)
pdf.indent_body(
    "(b)    During the Feasibility Period and throughout the Term, Owner shall cooperate with "
    "Tenant and shall execute all documents required to assist Tenant in obtaining all permits "
    "and to permit Tenant's intended use of the Premises and the Easements in compliance with "
    "zoning, land use, utility service and building laws, rules, ordinances, permits, approvals, "
    "variances and regulations, and any other applicable laws or regulations, including without "
    "limitation all requirements of the California Environmental Quality Act (CEQA), the "
    "Bureau of Land Management, the California Public Utilities Commission, and the San "
    "Bernardino County Planning Commission. Owner shall not take any action that would "
    "adversely affect Tenant's ability to obtain or maintain any governmental approval. Owner "
    "hereby appoints Tenant as its agent and attorney-in-fact for the limited purpose of making "
    "such filings and taking such actions as are necessary to obtain any desired zoning and land "
    "use approvals and/or building permits regarding the Project and the Premises and the "
    "Easements."
)
pdf.indent_body(
    "(c)    Owner shall take any and all actions requested by Tenant in a timely manner to cure "
    "any title defects, liens, claims or encumbrances which may interfere with Tenant's use and "
    "operation of the Premises and/or the Easements revealed in the Title Report, or any "
    'exceptions listed in any draft title commitment or pro forma developed from the Title Report '
    '("Title Defects"). Upon discovery of any such Title Defects, Tenant shall have the right, '
    "but not the obligation, to either (i) discharge or require Owner to discharge such Title "
    "Defects prior to the last day of the Feasibility Period, or (ii) terminate this Lease by "
    "providing written notice thereof to Owner."
)
pdf.indent_body(
    "(d)    Tenant shall pay for all costs incurred by it in connection with the Tests and its "
    "permitting and approval activities with regard to the Premises and the Easements and its "
    "general due diligence review of the Property."
)
pdf.indent_body(
    "(e)    Tenant may extend the Initial Feasibility Period for two (2) additional periods of "
    "three (3) months each (each a \"Feasibility Extension\") by providing written notice to "
    "Owner and paying a Feasibility Extension Payment of Twenty-Five Thousand Dollars "
    "($25,000.00) for each such extension."
)
pdf.indent_body(
    "(f)    If, in the sole and absolute discretion of Tenant, Tenant determines during the "
    "Feasibility Period that the Premises or the Property is not suitable for Tenant's intended use "
    "thereof, or Tenant determines that the construction and operation of the Project on the "
    "Property would not be economically feasible or in Tenant's best interest, or if Tenant is "
    "unsuccessful in obtaining the permits necessary for Tenant's intended use of the Property, "
    "or any title defects or exceptions to any draft title commitment cannot be cured or removed, "
    "then Tenant shall have the right at any time prior to the Lease Commencement Date to "
    "terminate this Agreement by providing written notice thereof to Owner."
)
pdf.indent_body(
    "(g)    Owner shall cooperate with Tenant's efforts to qualify the Project for any incentive "
    "program(s) available under applicable law, including but not limited to the Investment Tax "
    "Credit (ITC) under Section 48 of the Internal Revenue Code, any applicable state renewable "
    "energy incentives, and Renewable Energy Certificates (RECs), and shall provide commercially "
    "reasonable assistance necessary for Tenant to satisfy all required reporting obligations for "
    "the Project throughout the Term."
)

# ======== SECTION 5: USE ========
pdf.section_title("Section 5. Use.")
pdf.indent_body(
    "(a)    From and after the Commencement Date, Tenant is hereby granted the sole right to "
    "use the Premises for the purpose of constructing, installing, removing, replacing, "
    "reconstructing, maintaining and operating a solar array project, including solar panels, "
    "equipment, equipment shelters, single-axis tracking systems, canopy bays, and buildings, "
    "electronics equipment, battery energy storage technology and/or systems (including Tesla "
    "Megapack 2XL lithium-ion battery units), generators, transformers, switchgear, securing "
    "equipment, installation machines, tethers and other equipment, improvements and such "
    "other personal property, fencing and landscaping around the perimeter of the Premises or "
    "the portion thereof within which such Project shall be located (the \"Solar Compound\"), "
    "and a gate to the Solar Compound, all as described and depicted in Exhibit C attached "
    "hereto, as the same may be amended in accordance with the terms hereof (collectively, the "
    "\"Solar Facility\"). Owner hereby consents to the making of all such improvements from "
    "and after the Commencement Date. Any and all such materials installed by Tenant in, on "
    "or under the Property shall be deemed the personal property of Tenant, and shall not "
    "become fixtures or deemed a permanent part of the Property. Tenant shall have the right "
    "to alter, replace, expand, enhance and upgrade the Solar Facility within the Premises at "
    "any time during the term of this Lease."
)
pdf.indent_body(
    "(b)    Tenant shall use the Premises and such other areas of the Property as identified and "
    "depicted on the attached Exhibit B for solar energy conversion, battery energy storage, "
    "the collection and transmission of electrical energy to and from the Project, and for "
    "related and incidental purposes and activities, including but not limited to: (i) locating, "
    "constructing, installing, operating, maintaining, improving, repairing, relocating, and "
    "removing the Project on and from the Premises; (ii) parking in designated areas of the "
    "Property; (iii) accessing the Premises and the Project (including but not limited to access "
    "for lifting, rigging, and material-handling equipment); (iv) installing gates, fences, and "
    "such other security measures as may be necessary or desirable in Tenant's sole "
    "determination, to secure the Project; and (v) installing, maintaining, using, and repairing "
    "on the Premises, inverters, electrical wires, cables, substations, switching stations, and "
    "interconnection facilities required for the transmission of electrical energy to and from "
    "the Project to the point of interconnection with Southern California Edison at the Desert "
    "Bloom Switching Station."
)
pdf.indent_body(
    "(c)    This Agreement includes the right of ingress and egress to and from the Project over "
    "and across the Property for the purposes of installing, operating, maintaining, improving, "
    "repairing, relocating, and removing the Project on the Premises and to run wires, conduit, "
    "and fiber optic cables from the Project to the electrical panel, substation, and other areas "
    "within the Property, install any necessary fixtures to run such wires and conduit, and to "
    "obtain access to other utility services made available by the Owner."
)
pdf.indent_body(
    "(d)    Tenant shall keep and maintain the Solar Facility now or hereafter located on the "
    "Premises in good condition and repair, and shall maintain and operate the Solar Facility "
    "in material compliance with all applicable federal, state and local laws, rules, regulations, "
    "ordinances, permits, approvals and variances, including without limitation the rules and "
    "regulations of the California Independent System Operator (CAISO)."
)
pdf.indent_body(
    "(e)    Tenant may fence the Premises or the Solar Compound, provided that such fencing "
    "shall be installed so as to maintain reasonable access around the Premises by Tenant and "
    "Owner. Tenant shall have the right to clear and thereafter to keep clear the Premises and "
    "the Easements of all trees, bushes, rocks, and other vegetation using mechanical means "
    "subject to any restrictions and requirements of any buffer zones and setbacks required by "
    "local or state laws and permits and the requirements of any biological resource mitigation "
    "measures. No pesticides or herbicides shall be used at any time without approval by Owner "
    "and in compliance with applicable environmental law."
)
pdf.indent_body(
    "(f)    Tenant will pay for all utilities services used by Tenant at the Premises. Tenant "
    "shall have the right to cause utilities services to be installed at the Premises, at Tenant's "
    "sole expense, and to improve the present utilities services, including but not limited to "
    "the installation of emergency power generators, communication systems (including "
    "SCADA/DAS systems via Also Energy), meteorological stations, power lines, and utility "
    "poles."
)
pdf.indent_body(
    "(g)    As partial consideration for the Rent paid pursuant to this Lease, Owner hereby "
    "grants to Tenant and its successors and assigns, during the Term, easements in, under and "
    "across the Property: (i) for ingress, egress and access to the Premises, by foot and motor "
    "vehicles (including trucks and heavy construction equipment), (ii) to install utilities "
    "services at the Premises, (iii) to install storm water management systems; (iv) for the "
    "installation and maintenance of equipment, utility wires, poles, cables, conduits, drainage "
    "lines, and pipes to accommodate Tenant's permitted use of the Premises hereunder "
    "extending from the nearest public right-of-way, over and across any property of Owner "
    "to the Premises; (v) to capture, use and convert the unobstructed solar resources over and "
    "across the Property; and (vi) for electromagnetic, visual, view, light, noise, vibration, "
    'electrical, or other effects attributable to the Solar Facility (collectively, the "Easements").'
)

# ======== SECTION 6: TAXES ========
pdf.section_title("Section 6. Taxes and Assessments.")
pdf.body(
    "Tenant shall pay, prior to the date on which penalties attach thereto, all taxes, assessments and "
    "governmental charges of every description which during the Term hereof may be levied upon or "
    "assessed against the Premises, the Solar Facility, or any part thereof, or which may be imposed "
    "upon or become payable by the Tenant on account of or arising out of the ownership, operation, "
    "maintenance, alteration, repair, rebuilding, use or occupancy of the Premises or the Solar "
    "Facility, whether or not such taxes, assessments or charges are now customary or within the "
    "contemplation of the Parties. Tenant shall further pay all taxes assessed against the Solar "
    "Facility as personal property. Owner shall promptly forward to Tenant copies of all tax bills, "
    "assessment notices, and other governmental charges relating to the Premises within fifteen (15) "
    "business days of receipt thereof."
)

# ======== SECTION 7: ASSIGNMENT ========
pdf.section_title("Section 7. Assignment.")
pdf.indent_body(
    "(a)    Tenant may assign this Lease or any interest herein, or sublet the Premises or any "
    "portion thereof, upon written notice to Owner, without the need for Owner's consent, "
    "provided that: (i) the assignee or sublessee assumes all obligations of Tenant under this "
    "Lease; (ii) Tenant provides Owner with at least thirty (30) days' prior written notice of "
    "such assignment or subletting; and (iii) Tenant shall not be released from its obligations "
    "under this Lease by reason of any assignment unless expressly agreed in writing by Owner."
)
pdf.indent_body(
    "(b)    Tenant may, without Owner's consent, collaterally assign this Lease and/or grant a "
    "leasehold mortgage or security interest in Tenant's leasehold estate to any lender or "
    "financing party providing construction or permanent financing for the Project, including "
    "but not limited to KeyBank National Association (construction and permanent lender) and "
    "GreenVault Capital Partners (tax equity investor). Owner agrees to enter into a "
    "commercially reasonable consent and estoppel agreement with any such financing party."
)
pdf.indent_body(
    "(c)    Owner may transfer or assign Owner's interest in this Lease or the Premises, provided "
    "that any such transferee or assignee shall assume all obligations of Owner under this Lease "
    "and Owner shall provide Tenant with written notice of such transfer at least thirty (30) "
    "days in advance."
)

# ======== SECTION 8: SUBORDINATION ========
pdf.section_title("Section 8. Subordination.")
pdf.body(
    "This Lease and Tenant's interest in the Premises shall be subject and subordinate to any "
    "mortgage, deed of trust, or other lien or encumbrance that may now or hereafter encumber "
    "Owner's fee interest in the Property; provided, however, that Owner shall obtain from each "
    "holder of such mortgage, deed of trust, or lien a Subordination, Non-Disturbance and "
    "Attornment Agreement (\"SNDA\") in form and substance reasonably acceptable to Tenant "
    "and Tenant's lenders, pursuant to which such holder agrees that Tenant's possession of the "
    "Premises and rights under this Lease shall not be disturbed so long as Tenant is not in default "
    "under this Lease."
)

# ======== SECTION 9: SOLAR FACILITY OWNERSHIP ========
pdf.section_title("Section 9. Solar Facility Ownership and Solar Rights.")
pdf.indent_body(
    "(a)    The Solar Facility, including without limitation all photovoltaic panels, racking "
    "systems, single-axis trackers (NEXTracker NX Horizon), inverters (Sungrow SG250HX), "
    "transformers, switchgear, battery energy storage systems (Tesla Megapack 2XL), "
    "substation equipment, SCADA systems, meteorological stations, cables, fencing, and all "
    "other equipment and improvements installed by Tenant on the Premises, shall at all times "
    "remain the sole and exclusive personal property of Tenant and shall not be deemed "
    "fixtures or become part of the real property. Owner hereby waives any and all lien rights "
    "and/or security interests it may have, statutory or otherwise, in or with regard to the "
    "Solar Facility or any portion thereof."
)
pdf.indent_body(
    "(b)    Owner hereby grants to Tenant the exclusive right during the Term to capture, use, "
    "and convert all solar energy resources over, on, and across the Property to electrical "
    "energy. Neither Owner nor any third party shall install, operate, or maintain any solar "
    "energy generation or storage equipment on the Property or adjacent lands owned or "
    "controlled by Owner without the prior written consent of Tenant."
)

# ======== SECTION 10: REMOVAL ========
pdf.section_title("Section 10. Removal of Solar Facility; Decommissioning.")
pdf.body(
    "Upon the expiration or earlier termination of this Lease, Tenant shall, at its sole cost and "
    "expense, within twelve (12) months remove all above-ground improvements, equipment, and "
    "personal property comprising the Solar Facility from the Premises, and shall restore the "
    "surface of the Premises to a condition reasonably comparable to its condition prior to "
    "construction, normal wear and tear excepted. Tenant shall remove all concrete foundations "
    "to a depth of thirty-six (36) inches below grade. Tenant shall provide Owner with a "
    "Decommissioning Plan in the form attached hereto as Exhibit I, which shall be updated "
    "every five (5) years during the Term. Tenant shall maintain a decommissioning surety bond "
    "or letter of credit in an amount equal to the estimated net cost of decommissioning, less the "
    "salvage value of the Solar Facility components, such amount to be determined by a qualified "
    "independent engineer retained by Tenant. Tenant shall have the right at any time during "
    "the Term of this Lease to remove the Solar Facility from the Premises without the consent "
    "of the Owner."
)

# ======== SECTION 11: RESERVED ========
pdf.section_title("Section 11. [RESERVED]")
pdf.ln(2)

# ======== SECTION 12: INSURANCE ========
pdf.section_title("Section 12. Insurance.")
pdf.indent_body(
    "(a)    Tenant shall, at its own cost and expense, maintain, with a company or companies "
    "licensed or qualified to do business in the State of California and rated at least A-VII by "
    "A.M. Best, the following insurance coverages during the Term:"
)
pdf.indent_body(
    "    (i)    Commercial general liability insurance with limits not less than Five Million "
    "Dollars ($5,000,000.00) per occurrence and Ten Million Dollars ($10,000,000.00) in the "
    "aggregate for bodily injury, death, and property damage;", 20
)
pdf.indent_body(
    "    (ii)   Property insurance covering the Solar Facility in an amount not less than the "
    "full replacement cost thereof, currently estimated at Ninety-Five Million Dollars "
    "($95,000,000.00), including coverage for windstorm, earthquake, flood, fire, "
    "lightning, vandalism, and malicious mischief;", 20
)
pdf.indent_body(
    "    (iii)  Business interruption insurance for a period of twelve (12) months;", 20
)
pdf.indent_body(
    "    (iv)   Workers' compensation insurance as required by applicable law, with "
    "employer's liability limits of at least One Million Dollars ($1,000,000.00);", 20
)
pdf.indent_body(
    "    (v)    Automobile liability insurance with a combined single limit of not less "
    "than One Million Dollars ($1,000,000.00).", 20
)
pdf.indent_body(
    "(b)    Owner shall be named as an additional insured under Tenant's commercial general "
    "liability policy. Owner shall maintain commercial general liability insurance with limits "
    "not less than Two Million Dollars ($2,000,000.00) per occurrence. Tenant shall be an "
    "additional insured under Owner's policy."
)
pdf.indent_body(
    "(c)    The current insurance provider is Marsh McLennan Energy Practice, 1166 Avenue "
    "of the Americas, New York, NY 10036. The current annual premium is Two Hundred "
    "Eighty-Five Thousand Dollars ($285,000.00). The named storm deductible shall be three "
    "percent (3%) of property value."
)

# ======== SECTION 13: TERMINATION ========
pdf.section_title("Section 13. Termination.")
pdf.body(
    "Tenant may terminate this Agreement at any time during the Feasibility Period, in its sole "
    "discretion, by giving written notice thereof to Owner. Further, this Agreement may be "
    "terminated by Tenant immediately, at any time, upon giving written notice to Owner, if: "
    "(a) Tenant cannot obtain all governmental certificates, permits, variances, leases or other "
    "approvals required for the installation and operation of the Solar Facility at the Premises; "
    "(b) any such approval is canceled, terminated, or expires; (c) Owner fails to deliver to "
    "Tenant any curative document related to a Title Defect or non-disturbance agreement or "
    "subordination agreement required hereunder; (d) Owner fails to have proper ownership of "
    "the Property and/or authority to enter into this Agreement; (e) Tenant determines that the "
    "Property contains Hazardous Substances not introduced by Tenant; or (f) Owner is in "
    "default hereunder and fails to cure such default within the periods specified in Section 18."
)

# ======== SECTION 14: INDEMNITY ========
pdf.section_title("Section 14. Indemnity.")
pdf.body(
    "Owner and Tenant each agree to indemnify and hold harmless the other Party from and against "
    "any and all claims, losses, liabilities, obligations, damages, costs and expenses, including "
    'reasonable attorney fees (collectively, the "Losses"), to the extent caused by or arising out of '
    "(a) the acts or omissions of such Party in the operations or activities on the Property, the "
    "Premises and/or the Easements by the indemnifying Party or the employees, affiliates, agents, "
    "contractors, licensees, tenants and/or subtenants of the indemnifying Party, or (b) a breach of "
    "or default by the indemnifying Party under this Lease that has not been cured in accordance "
    "with the terms hereof. Notwithstanding the foregoing, this indemnification shall not extend to "
    "Losses exclusively arising from the negligence or intentional misconduct of the indemnified "
    "Party. NOTWITHSTANDING ANYTHING ELSE CONTAINED IN THIS CLAUSE, NEITHER "
    "PARTY SHALL BE LIABLE TO THE OTHER PARTY FOR ANY SPECIAL, CONSEQUENTIAL, "
    "PUNITIVE, EXEMPLARY OR OTHER EXTRAORDINARY DAMAGES. NEITHER PARTY SHALL "
    "HAVE ANY RIGHT TO INDEMNIFICATION IN THE CASE OF FORCE MAJEURE."
)

# ======== SECTION 15: HAZARDOUS SUBSTANCES ========
pdf.section_title("Section 15. Hazardous Substances.")
pdf.indent_body(
    "(a)    Owner hereby represents and warrants that it has no knowledge of any substance, "
    'chemical or waste (collectively, the "Hazardous Substances") on the Property that is '
    "identified as hazardous, toxic or dangerous in any applicable federal, state or local law "
    "or regulation, including without limitation the Comprehensive Environmental Response, "
    "Compensation and Liability Act (CERCLA), the Resource Conservation and Recovery Act "
    "(RCRA), the California Hazardous Waste Control Law, and Title 22 of the California Code "
    "of Regulations, except as identified and disclosed in any environmental reports prepared "
    "for Owner or Tenant."
)
pdf.indent_body(
    "(b)    Tenant hereby represents and warrants that it shall not: (i) bury underground or "
    "discharge into the sewage system at the Premises any Hazardous Substances, or (ii) use "
    "the Premises as a storage site for Hazardous Substances, except minimal quantities used "
    "in the ordinary course of Tenant's business in accordance with all applicable environmental "
    "laws and regulations, including lubricants, coolants, and electrolyte solutions used in "
    "connection with the battery energy storage system."
)
pdf.indent_body(
    "(c)    Owner shall, without limitation, defend, indemnify and hold harmless Tenant from "
    "and against any and all claims or losses concerning hazardous substances or any other "
    "environmental harm or damage not caused by Tenant."
)

# ======== SECTION 16: CASUALTY AND CONDEMNATION ========
pdf.section_title("Section 16. Casualty and/or Condemnation.")
pdf.indent_body(
    "(a)    If there is a condemnation of the Premises, the Easements and/or the Property (or a "
    "portion thereof which is sufficient to render the Premises unsuitable for Tenant's purposes, "
    "in its sole discretion), then this Lease shall, at the option of Tenant, terminate upon transfer "
    "of title to the condemning authority, without further liability to either Party hereunder. "
    "The Rent due hereunder shall be prorated to the date of taking, and Owner shall reimburse "
    "to Tenant any portion of the then current annual Rent attributable to the period subsequent "
    "to such taking."
)
pdf.indent_body(
    "(b)    If the Premises are damaged or destroyed to an extent sufficient to render the Premises "
    "unsuitable for Tenant's purposes, in Tenant's sole determination, Tenant shall have the "
    "right, but not the obligation, to elect to not rebuild and to terminate this Lease as of the "
    "date that such damage or destruction occurred."
)
pdf.indent_body(
    "(c)    Notwithstanding anything in this Agreement to the contrary, in the event of any "
    "casualty to or condemnation of the Property during such time as any Security Instrument "
    "shall remain unsatisfied, the Financing Entity in whose favor such Security Instrument "
    "has been granted shall be entitled to receive all insurance proceeds and/or condemnation "
    "awards (up to the amount of the indebtedness secured by such Security Instrument) and "
    "apply such proceeds in accordance with the terms of the Security Instrument."
)

# ======== SECTION 17: QUIET ENJOYMENT ========
pdf.section_title("Section 17. Quiet Enjoyment.")
pdf.indent_body(
    "(a)    Owner covenants that Tenant, upon paying the Rent and performing the covenants "
    "hereof on the part of Tenant to be performed, shall and may peaceably and quietly have, "
    "hold and enjoy the Premises and the Easements and all related appurtenances, rights, "
    "privileges and easements throughout the Term hereof without any lawful hindrance by "
    "Owner and any person claiming by, through or under Owner. Except in cases of emergency, "
    "Owner shall not have access to the Premises unless accompanied by Tenant personnel."
)
pdf.indent_body(
    "(b)    The Solar Facility shall be the exclusive property of and owned by Tenant. Owner "
    "covenants and agrees that neither the Solar Facility nor any part of the improvements "
    "constructed, erected or placed by Tenant on the Premises or the Easements shall become "
    "or be considered as being affixed to or a part of the Premises or the Easements."
)
pdf.indent_body(
    "(c)    If Owner owns or otherwise controls land adjacent to the Premises, Owner agrees "
    "for itself and all future holders of the Property that no use shall be made of such adjacent "
    "land during the Term that would materially interfere with Tenant's use of the Premises, "
    "including, without limitation, the operation of any solar facilities by any Party other than "
    "Tenant, the erection of structures that would cast shadows upon the Solar Facility, or the "
    "planting of vegetation that would obstruct sunlight."
)
pdf.indent_body(
    "(d)    Owner hereby represents and warrants to Tenant that: (i) Owner is the fee owner of "
    "the Property; (ii) such ownership is free and clear of all liens, claims and encumbrances "
    "that interfere with Tenant's use; (iii) Owner has the lawful right and authority to execute "
    "this Lease; (iv) the Property is in substantial compliance with all applicable laws; and "
    "(v) Owner has obtained and delivered to Tenant the consents of all Parties that hold any "
    "encumbrance upon or interest in the Premises."
)

# ======== SECTION 18: DEFAULT ========
pdf.section_title("Section 18. Default.")
pdf.indent_body(
    "(a)    Notwithstanding anything contained herein to the contrary, if either Party is in default "
    "under this Lease for a period of (i) ten (10) days following receipt of notice of default from "
    "the non-defaulting Party with respect to a default which may be cured solely by the payment "
    "of money, (ii) thirty (30) days following receipt of notice from Tenant if Owner shall "
    "violate, neglect or fail to perform or observe any of the representations, covenants, "
    "provisions, or conditions contained in this Lease; or (iii) sixty (60) days following receipt "
    "of notice of default from the non-defaulting Party with respect to any other default, then "
    "the non-defaulting Party shall have the remedies detailed in Section 18(b) hereof."
)
pdf.indent_body(
    "(b)    If an event of default is ongoing after the cure periods detailed in Section 18(a), the "
    "Parties shall have the following rights:\n\n"
    "    (i) Termination. Either Party may terminate this Lease upon thirty (30) days' notice.\n\n"
    "    (ii) Payment of Termination Payment for Owner Default. If Tenant terminates this "
    "Agreement as a result of an Owner default, Owner shall pay to Tenant a termination "
    "payment equal to the fair market value of Tenant's remaining leasehold interest.\n\n"
    "    (iii) Tenant Right to Cure. In the event that Owner fails to cure any default, Tenant "
    "may incur any reasonable expense necessary to perform the obligation of Owner and "
    "deduct such costs from Rent."
)

# ======== SECTION 19: COLLATERAL ASSIGNMENT ========
pdf.section_title("Section 19. Collateral Assignment.")
pdf.indent_body(
    "(a)    Tenant may collaterally assign, pledge, mortgage and/or grant a security interest to "
    'any third Party (each, a "Financing Entity"), as security for any loan or other financing '
    "relationship, all of Tenant's right, title and interest in: (i) this Agreement; (ii) the "
    "Premises; (iii) the Easements; (iv) the Solar Facility; and (v) any other personal property "
    "owned by Tenant and located at the Property, all without the consent of Owner."
)
pdf.indent_body(
    "(b)    Financing Entity may: (i) enforce its rights under its leasehold mortgage and/or "
    'other loan and security documents (each, a "Security Instrument"); (ii) acquire title to '
    "Tenant's interest in the Premises under this Agreement in any lawful way; (iii) pending "
    "foreclosure, take possession of the Premises; and (iv) obtain a title insurance policy."
)

# ======== SECTION 20: ESTOPPEL ========
pdf.section_title("Section 20. Estoppel Certificates.")
pdf.body(
    "Owner shall from time to time, within ten (10) days after receipt of Tenant's written request "
    "therefor, deliver to Tenant a written statement addressed to Tenant and/or to any Financing "
    "Entity (as specified by Tenant), substantially in the form of Exhibit G hereof."
)

# ======== SECTION 21: MORTGAGE PROTECTION ========
pdf.section_title("Section 21. Mortgage Protection.")
pdf.body(
    "The following provisions shall be effective at any time that Owner has received notice that "
    "Tenant has mortgaged its leasehold interest under this Lease and/or granted a security interest "
    "in the Solar Facility. After receipt by Tenant of a notice of default under this Lease and the "
    "expiration of any applicable cure period hereunder, Owner shall deliver to each Financing Entity "
    'that holds a Security Instrument an additional notice (the "Financing Entity Notice") which '
    "specifies the default by Tenant and states that Tenant's cure period has expired. Each such "
    "Financing Entity shall thereupon have the right, but not the obligation, to cure such default "
    "within thirty (30) days for non-monetary defaults and fifteen (15) days for monetary defaults."
)

# ======== SECTION 22: MISCELLANEOUS ========
pdf.section_title("Section 22. Miscellaneous Provisions.")
pdf.indent_body(
    "(a)    Force Majeure. Neither party shall be in default if failure to perform is due to causes "
    "beyond its reasonable control, including but not limited to acts of God, acts of government, "
    "fire, earthquake, flood, drought, epidemic, pandemic, labor disputes, material shortages, "
    "power outages, war, terrorism, civil unrest, or inability to obtain necessary permits or "
    "governmental approvals despite diligent efforts. The affected party shall promptly notify "
    "the other party in writing of the nature and expected duration of such Force Majeure event."
)
pdf.indent_body(
    "(b)    Notices. All notices, requests, demands, and other communications hereunder shall "
    "be in writing and shall be delivered by hand, by nationally recognized overnight delivery "
    "service, or by United States mail, certified or registered, return receipt requested, postage "
    "prepaid, to the addresses set forth on the Cover Sheet."
)
pdf.indent_body(
    "(c)    Governing Law. This Lease shall be governed by and construed in accordance with "
    "the laws of the State of California, without regard to conflicts of law principles. Any "
    "dispute arising under this Lease shall be submitted to binding arbitration in San "
    "Bernardino County, California, in accordance with the Commercial Arbitration Rules of "
    "the American Arbitration Association."
)
pdf.indent_body(
    "(d)    Entire Agreement. This Lease, including all Exhibits attached hereto, constitutes the "
    "entire agreement between the Parties and supersedes all prior negotiations, "
    "representations, and agreements."
)
pdf.indent_body(
    "(e)    Binding Effect. This Lease shall be binding upon and inure to the benefit of the "
    "Parties hereto and their respective successors, personal representatives, heirs and assigns."
)
pdf.indent_body(
    "(f)    Severability. If any provision of this Lease is found by a court of competent "
    "jurisdiction to be unenforceable or illegal, the remainder of this Lease shall be enforceable "
    "as if such provision had not been contained herein."
)
pdf.indent_body(
    "(g)    Confidentiality. Neither Tenant nor Owner shall disclose the financial or other terms "
    "of this Agreement to third Parties (other than either Party's employees, attorneys, lenders, "
    "accountants, and tax equity investors) without the express written consent of the "
    "non-disclosing Party."
)
pdf.indent_body(
    "(h)    Amendments. This Agreement may not be amended, supplemented or restated except "
    "by a written instrument that has been executed and delivered by each of the Parties hereto."
)
pdf.indent_body(
    "(i)    Waiver. The waiver by any Party hereto of a breach of any provision of this Lease "
    "shall not bar or be construed as a waiver of any subsequent breach by any Party."
)
pdf.indent_body(
    "(j)    Counterparts. This Agreement may be executed in counterparts, each of which shall "
    "be deemed an original, and all of which together shall constitute one and the same "
    "instrument. Electronic or facsimile signatures shall be deemed original signatures."
)

# ======== SIGNATURE PAGES ========
pdf.add_page()
pdf.ln(5)
pdf.set_font("Helvetica", "I", 10)
pdf.cell(0, 8, "[This Space Left Blank Intentionally; Signatures Appear Below]", align="C",
         new_x="LMARGIN", new_y="NEXT")
pdf.ln(15)

pdf.set_font("Helvetica", "", 10)
pdf.body("IN WITNESS WHEREOF, the Parties hereto have executed this Ground Lease Agreement "
         "as of the day and year first above written.")
pdf.ln(10)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "OWNER:", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 6, "Mojave Solar Ranch LLC", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "a California limited liability company", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.cell(0, 6, "By: ___________________________", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Name: Robert J. Caldwell", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Title: Managing Member", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Date: June 15, 2023", new_x="LMARGIN", new_y="NEXT")

pdf.ln(15)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "TENANT:", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 6, "Desert Bloom Solar LLC", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "a Delaware limited liability company", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.cell(0, 6, "By: ___________________________", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Name: Victoria Chen", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Title: President, Solara Holdings LLC (sole member)", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Date: June 15, 2023", new_x="LMARGIN", new_y="NEXT")

# ======== NOTARIZATION ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "ACKNOWLEDGMENT - OWNER", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)
pdf.body(
    "STATE OF CALIFORNIA\n"
    "COUNTY OF SAN BERNARDINO, ss.\n\n"
    "On this 15th day of June, 2023, before me, the undersigned notary public, personally "
    "appeared Robert J. Caldwell, as Managing Member of Mojave Solar Ranch LLC, a California "
    "limited liability company, proved to me through satisfactory evidence of identity, and "
    "acknowledged to me that he signed the foregoing Ground Lease Agreement voluntarily and "
    "for its stated purpose in the aforesaid capacity."
)
pdf.ln(10)
pdf.cell(0, 6, "___________________________", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Notary Public", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "My Commission Expires: March 14, 2027", new_x="LMARGIN", new_y="NEXT")

pdf.ln(20)
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "ACKNOWLEDGMENT - TENANT", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)
pdf.body(
    "STATE OF COLORADO\n"
    "COUNTY OF DENVER, ss.\n\n"
    "On this 15th day of June, 2023, before me, the undersigned notary public, personally "
    "appeared Victoria Chen, as President of Solara Holdings LLC, the sole member of Desert "
    "Bloom Solar LLC, a Delaware limited liability company, proved to me through satisfactory "
    "evidence of identity, and acknowledged to me that she signed the foregoing Ground Lease "
    "Agreement voluntarily and for its stated purpose in the aforesaid capacity."
)
pdf.ln(10)
pdf.cell(0, 6, "___________________________", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Notary Public", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "My Commission Expires: September 30, 2026", new_x="LMARGIN", new_y="NEXT")

# ======== EXHIBIT A ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT A", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "LEGAL DESCRIPTION OF PROPERTY", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.body(
    "All that certain real property situated in the County of San Bernardino, State of California, "
    "described as follows:\n\n"
    "Assessor's Parcel Numbers: 0529-161-01, 0529-161-02, 0529-162-01, and 0529-162-03\n\n"
    "Portions of Sections 14 and 15, Township 10 North, Range 1 East, San Bernardino Base "
    "and Meridian, more particularly described as:\n\n"
    "BEGINNING at the Northeast corner of Section 15, Township 10 North, Range 1 East, San "
    "Bernardino Base and Meridian; thence South 00 degrees 02 minutes 18 seconds West along "
    "the East line of said Section 15, a distance of 5,280.00 feet; thence North 89 degrees 57 "
    "minutes 42 seconds West, a distance of 3,960.00 feet; thence North 00 degrees 02 minutes "
    "18 seconds East, a distance of 5,280.00 feet to the North line of said Section 15; thence "
    "South 89 degrees 57 minutes 42 seconds East along said North line, a distance of 3,960.00 "
    "feet to the POINT OF BEGINNING.\n\n"
    "TOGETHER WITH portions of the Northwest Quarter (NW 1/4) of Section 14, Township 10 "
    "North, Range 1 East, described as:\n\n"
    "BEGINNING at the Northwest corner of Section 14; thence South 00 degrees 01 minutes 44 "
    "seconds West along the West line of said Section 14, a distance of 2,640.00 feet; thence "
    "South 89 degrees 58 minutes 16 seconds East, a distance of 2,640.00 feet; thence North 00 "
    "degrees 01 minutes 44 seconds East, a distance of 2,640.00 feet to the North line of said "
    "Section 14; thence North 89 degrees 58 minutes 16 seconds West along said North line, a "
    "distance of 2,640.00 feet to the POINT OF BEGINNING.\n\n"
    "Containing approximately 480 acres, more or less.\n\n"
    "Subject to all easements, restrictions, and rights-of-way of record.\n\n"
    "Bearings herein are based on Grid North, California Coordinate System, Zone 5, NAD83 "
    "(2011 Epoch 2010.00).\n\n"
    "For purposes of reference only, the above-described premises is identified as portions of "
    "San Bernardino County Assessor's Parcels 0529-161-01, 0529-161-02, 0529-162-01, and "
    "0529-162-03.\n\n"
    "EXCEPTING AND RESERVING UNTO THE GRANTOR, its successors and assigns, an easement "
    "and right of way for the benefit of Grantor's remaining property, for ingress and egress by "
    "vehicles and pedestrians (with the right to improve the surface, including but not limited to "
    "grading and paving) and to install, maintain, repair and replace any underground or above "
    "ground utilities over, under and across the following described access corridor:\n\n"
    "A strip of land thirty (30) feet in width, fifteen (15) feet on either side of the centerline of "
    "the existing unpaved access road extending from the northerly boundary of the Property "
    "southward to Mojave Desert Highway (State Route 247), being approximately 1,200 linear "
    "feet in length and containing approximately 0.83 acres.\n\n"
    "Bearings contained herein are based on Grid North, California Coordinate System, Zone 5, "
    "NAD83 (2011 Epoch 2010.00)."
)

# ======== EXHIBIT B ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT B", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "LEGAL DESCRIPTION OF THE PREMISES AND THE EASEMENTS", align="C",
         new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.body(
    "The Premises shall consist of the entirety of the Property described in Exhibit A, "
    "subject to the reserved access corridor easement described therein.\n\n"
    "The Premises include the following designated areas:\n\n"
    "1. Solar Array Area: Approximately 420 acres, comprising the photovoltaic panel arrays "
    "arranged in single-axis tracking rows oriented north-south, with a ground coverage ratio "
    "of 0.33 and center-to-center row spacing of 6.5 meters.\n\n"
    "2. Battery Energy Storage Area: Approximately 5 acres, located adjacent to the project "
    "substation, housing four (4) Tesla Megapack 2XL battery units with associated balance-of-"
    "system equipment, thermal management systems, and fire suppression infrastructure.\n\n"
    "3. Substation and Interconnection Area: Approximately 3 acres, housing the project "
    "substation, step-up transformers (34.5 kV to 115 kV), switchgear, metering equipment, "
    "and interconnection facilities connecting to the Southern California Edison transmission "
    "system at the Desert Bloom Switching Station.\n\n"
    "4. Operations and Maintenance Building Area: Approximately 1 acre, including a "
    "prefabricated O&M building, spare parts storage, tool shed, and vehicle parking.\n\n"
    "5. Access Roads: Approximately 15 acres of internal access roads providing maintenance "
    "access to all array blocks, the substation, and the BESS area.\n\n"
    "6. Perimeter Buffer and Drainage: Approximately 36 acres, comprising perimeter setbacks, "
    "stormwater management features, and biological resource buffer areas.\n\n"
    "The Easements granted hereunder shall include:\n\n"
    "(a) An access easement extending from Mojave Desert Highway (State Route 247) to the "
    "Project entrance gate, being a strip of land fifty (50) feet in width.\n\n"
    "(b) A utility easement for the installation and maintenance of electrical transmission "
    "lines, fiber optic communication cables, and water supply lines, extending from the "
    "project substation to the point of interconnection with the SCE transmission system, "
    "being a strip of land forty (40) feet in width.\n\n"
    "(c) A drainage easement for stormwater management, extending along the natural "
    "drainage courses crossing or adjacent to the Property."
)

# ======== EXHIBIT C ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT C", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "PROPOSED DEPICTION OF THE SOLAR FACILITY", align="C",
         new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.body(
    "The location and the size of the Solar Facility is subject to change based on existing "
    "conditions, environmental surveys, geotechnical investigation, permitting, and feedback "
    "from Southern California Edison and the California Independent System Operator.\n\n"
    "[Site Plan prepared by SunBuild Energy Solutions, dated September 15, 2023, Drawing "
    "Number DB-SP-001, Rev. 3 - to be inserted]\n\n"
    "PROJECT SPECIFICATIONS:\n\n"
    "System Size (DC): 98.5 MWp\n"
    "System Size (AC): 75.0 MW\n"
    "DC/AC Ratio: 1.313\n"
    "Module Technology: LONGi LR5-72HBD-545M Bifacial Mono PERC\n"
    "Module Quantity: 180,734 modules\n"
    "Inverter: Sungrow SG250HX (12 units)\n"
    "Tracking System: NEXTracker NX Horizon Single-Axis\n"
    "Battery Storage: Tesla Megapack 2XL (4 units, 15,664 kWh / 7,648 kW)\n"
    "Revenue Meter: ION 8650 (Accuracy Class 0.2S)\n"
    "Weather Station: Campbell CR1000X\n"
    "DAS Provider: Also Energy\n"
    "Interconnection: 115 kV at Desert Bloom Switching Station (SCE)\n"
    "Fencing: 8-foot chain link with 3-strand barbed wire top, NESC compliant"
)

# ======== EXHIBIT D ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT D", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "MEMORANDUM/NOTICE OF LEASE", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "NOTICE OF LEASE", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
pdf.body(
    "In accordance with the provisions of California Civil Code Section 1214 and California "
    "Government Code Section 27281.5, notice is hereby given of the Ground Lease Agreement "
    "for Solar Project (the \"Lease\") dated of even date herewith."
)

notice_fields = [
    ("LANDLORD:", "Mojave Solar Ranch LLC, with a mailing address of\n"
     "45200 National Trails Highway, Newberry Springs, CA 92365"),
    ("TENANT:", "Desert Bloom Solar LLC, with a mailing address of\n"
     "100 Solar Innovation Drive, Denver, CO 80202"),
    ("DESCRIPTION OF\nLEASED PREMISES:", "The Leased Premises consists of approximately 480 acres\n"
     "located at 12500 Mojave Desert Highway, Barstow, CA 92311\n"
     "San Bernardino County, California, more particularly\n"
     "described in Exhibit A attached hereto."),
    ("EFFECTIVE DATE:", "June 15, 2023"),
    ("COMMENCEMENT DATE:", "To be determined upon Tenant's notice to proceed."),
    ("TERM:", "Twenty-five (25) years from Commercial Operation Date"),
    ("RENEWAL TERMS:", "Two (2) additional five (5) year terms"),
    ("NO FIXTURE:", "The Solar Facility installed and operated by Tenant at the\n"
     "Leased Premises shall not be deemed a fixture. The Solar\n"
     "Facility is Tenant's personal property and Landlord has no\n"
     "right, title or interest in the Solar Facility."),
    ("EXCLUSIVE RIGHT:", "Tenant shall have the sole and exclusive right to convert\n"
     "and store all solar energy resources of the Property to\n"
     "electrical energy during the term of the Lease."),
]
for label, value in notice_fields:
    pdf.cover_field(label, value, lw=45)
    pdf.ln(2)

pdf.ln(5)
pdf.body(
    "IN WITNESS WHEREOF, the parties hereto have set their hands and seal as of the 15th day "
    "of June, 2023."
)
pdf.ln(8)
for party in [("OWNER:", "Mojave Solar Ranch LLC", "Robert J. Caldwell", "Managing Member"),
              ("TENANT:", "Desert Bloom Solar LLC", "Victoria Chen", "President, Solara Holdings LLC")]:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, party[0], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, party[1], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"By: ___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Name: {party[2]}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Title: {party[3]}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

# ======== EXHIBIT E ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT E", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "LANDLORD ESTOPPEL CERTIFICATE AND AGREEMENT", align="C",
         new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.body(
    "Desert Bloom Solar LLC\n"
    "c/o Solara Holdings LLC\n"
    "100 Solar Innovation Drive\n"
    "Denver, CO 80202\n\n"
    "Re: Ground Lease Agreement for Solar Project dated June 15, 2023 (the \"Lease\") by and "
    "between Mojave Solar Ranch LLC, a California limited liability company (\"Landlord\") and "
    "Desert Bloom Solar LLC, a Delaware limited liability company (the \"Tenant\") for the "
    "premises located at 12500 Mojave Desert Highway, Barstow, San Bernardino County, "
    "California 92311 (the \"Leased Premises\")\n\n"
    "Ladies and Gentlemen:\n\n"
    "The undersigned Landlord does hereby certify to Tenant and Investor (GreenVault Capital "
    "Partners), and their successors and assigns, their potential lenders (KeyBank National "
    "Association) and their members, managers and other participants, and their respective "
    "successors and assigns, as follows:\n\n"
    "1. Until such time as all liabilities and obligations of Tenant and its affiliates to Lender "
    "have been paid and performed in full, Landlord hereby waives, releases and relinquishes "
    "to Lender all right, title, interest, claim and lien which Landlord has or may have in, to "
    "or against any assets and other personal property of Tenant, including without limitation, "
    "solar panels, trackers, inverters, transformers, battery storage systems, racking, inventory, "
    "equipment, machinery, and all other personal property located at any time on the Leased "
    "Premises.\n\n"
    "2. Landlord authorizes Lender, its attorneys, agents and employees to enter on the Leased "
    "Premises and to take possession of, remove or dispose of the Personal Property at any "
    "time.\n\n"
    "3. The Personal Property is not and shall not be deemed a fixture or part of the real "
    "estate.\n\n"
    "4. Landlord has not received notification of any other entity (other than Lender) claiming "
    "a security interest in the Personal Property.\n\n"
    "5. A true and correct copy of the Lease is attached hereto as Exhibit A; the Lease is in "
    "full force and effect; all amounts due have been paid; and Landlord has not given Tenant "
    "written notice of any dispute or default."
)

# ======== EXHIBIT G ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT G", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "FORM OF ESTOPPEL CERTIFICATE", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.body(
    "[To be completed by Landlord upon request by Tenant]\n\n"
    "The undersigned hereby certifies as follows:\n\n"
    "1. The Lease is in full force and effect and has not been modified, amended or supplemented "
    "except as follows: [none / list modifications].\n\n"
    "2. The Lease represents the entire agreement between Landlord and Tenant.\n\n"
    "3. To Landlord's knowledge, there are no uncured defaults by Tenant under the Lease.\n\n"
    "4. To Landlord's knowledge, there are no uncured defaults by Landlord under the Lease.\n\n"
    "5. The current annual Base Rent is $__________ per annum.\n\n"
    "6. Rent has been paid through __________.\n\n"
    "7. The Commencement Date of the Lease was __________.\n\n"
    "8. The Commercial Operation Date was __________.\n\n"
    "9. The current expiration date of the Lease is __________.\n\n"
    "10. Tenant has _____ remaining Renewal Options of five (5) years each."
)

# ======== EXHIBIT H ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT H", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "RENT SCHEDULE", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)
pdf.body(
    "The following schedule sets forth the Base Rent for each Lease Year, reflecting the annual "
    "escalation of 2.0% as provided in Section 3(c) of this Lease:"
)
pdf.ln(2)

pdf.set_font("Helvetica", "B", 9)
pdf.cell(25, 7, "Lease Year", border=1, align="C")
pdf.cell(40, 7, "Period", border=1, align="C")
pdf.cell(35, 7, "Annual Rent", border=1, align="C")
pdf.cell(35, 7, "Monthly Rent", border=1, align="C")
pdf.cell(25, 7, "Escalation", border=1, align="C")
pdf.ln()

pdf.set_font("Helvetica", "", 9)
rent = 185000.00
for yr in range(1, 26):
    start = 2022 + yr
    end = 2023 + yr
    monthly = rent / 12
    esc = "---" if yr == 1 else "2.0%"
    pdf.cell(25, 5, str(yr), border=1, align="C")
    pdf.cell(40, 5, f"{start}-{end}", border=1, align="C")
    pdf.cell(35, 5, f"${rent:,.2f}", border=1, align="R")
    pdf.cell(35, 5, f"${monthly:,.2f}", border=1, align="R")
    pdf.cell(25, 5, esc, border=1, align="C")
    pdf.ln()
    rent *= 1.02

pdf.ln(4)
pdf.body(
    "Renewal Term Rent: During any Renewal Term, the Base Rent shall continue to escalate "
    "at two percent (2.0%) per annum."
)

# ======== EXHIBIT I ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT I", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "DECOMMISSIONING PLAN AND FINANCIAL ASSURANCE", align="C",
         new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.body(
    "1. SCOPE OF DECOMMISSIONING\n\n"
    "Upon expiration or earlier termination of the Lease, Tenant shall decommission the Solar "
    "Facility and restore the Premises in accordance with the following plan:\n\n"
    "    (a) Remove all photovoltaic modules, racking systems, and single-axis trackers;\n"
    "    (b) Remove all inverters, transformers, switchgear, and electrical equipment;\n"
    "    (c) Remove all battery energy storage system components, including batteries,\n"
    "        thermal management systems, and enclosures;\n"
    "    (d) Remove all above-ground electrical conduit, cables, and wiring;\n"
    "    (e) Remove all concrete foundations and piers to a depth of 36 inches below grade;\n"
    "    (f) Remove all fencing, gates, and security equipment;\n"
    "    (g) Remove all access roads unless Owner elects to retain them;\n"
    "    (h) Remove all buildings, structures, and ancillary facilities;\n"
    "    (i) Restore the ground surface to pre-construction contours;\n"
    "    (j) Revegetate disturbed areas with native species.\n\n"
    "2. ESTIMATED DECOMMISSIONING COSTS\n\n"
    "    Gross Decommissioning Cost:        $8,500,000\n"
    "    Less: Estimated Salvage Value:    ($3,200,000)\n"
    "    Net Decommissioning Cost:          $5,300,000\n\n"
    "    Salvage value estimate includes:\n"
    "    - Photovoltaic modules:            $1,200,000\n"
    "    - Copper and aluminum cable/wire:    $450,000\n"
    "    - Steel racking and trackers:        $800,000\n"
    "    - Inverters and transformers:        $350,000\n"
    "    - Battery system components:         $400,000\n\n"
    "3. FINANCIAL ASSURANCE\n\n"
    "Tenant shall maintain a decommissioning surety bond or irrevocable letter of credit in an "
    "amount equal to the estimated net decommissioning cost, adjusted every five (5) years "
    "based on an updated cost estimate prepared by a qualified independent engineer. The "
    "current financial assurance amount is $5,300,000.\n\n"
    "4. TIMELINE\n\n"
    "Decommissioning shall be completed within twelve (12) months following the expiration or "
    "termination of the Lease, subject to force majeure and permitting requirements."
)

# ======== EXHIBIT F ========
pdf.add_page()
pdf.set_font("Helvetica", "B", 14)
pdf.cell(0, 10, "EXHIBIT F", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "FORM OF EASEMENT", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 8, "ACCESS, UTILITY AND DRAINAGE EASEMENT AGREEMENT", align="C",
         new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
pdf.body(
    "This ACCESS, UTILITY AND DRAINAGE EASEMENT (the \"Easement Agreement\") is made "
    "and executed as of this 15th day of June, 2023, by and between Desert Bloom Solar LLC, a "
    "Delaware limited liability company, having a business address of 100 Solar Innovation "
    "Drive, Denver, CO 80202 (\"Grantee\") and Mojave Solar Ranch LLC, a California limited "
    "liability company, with an address of 45200 National Trails Highway, Newberry Springs, "
    "CA 92365 (\"Grantor\").\n\n"
    "WHEREAS, Grantor is the owner of record of certain real property located at 12500 Mojave "
    "Desert Highway, Barstow, San Bernardino County, California 92311, more particularly "
    "described on Exhibit A attached hereto (the \"Landlord Property\");\n\n"
    "WHEREAS, Grantee has entered into a Ground Lease Agreement for Solar Project with the "
    "Grantor dated June 15, 2023, as amended, (the \"Lease\") to lease the Landlord Property;\n\n"
    "WHEREAS Grantee desires to access the Leased Property via access roads, and place "
    "certain utility related equipment on said roads (the \"Access and Utility Easement Area\");\n\n"
    "WHEREAS Grantee desires to utilize certain land for drainage improvements (the \"Access "
    "and Drainage Easement Area\");\n\n"
    "NOW, THEREFORE, for good and valuable consideration, the parties agree as follows:\n\n"
    "1. Grant of Access and Utility Easement.\n\n"
    "    (a) Access Easement. Grantor hereby grants to Grantee a non-exclusive easement "
    "of limited duration to enter, re-enter and use any portion of the Access and Utility "
    "Easement Area for unobstructed ingress and egress to the Leased Property in connection "
    "with the construction, operation and maintenance of the Solar Facility.\n\n"
    "    (b) Utility Easement. Grantor hereby grants to Grantee a non-exclusive easement "
    "to install, construct, reconstruct, alter, extend, operate, inspect, maintain, repair, "
    "replace and remove utility poles, overhead and underground wires, cables, transformers, "
    "switchgear, pedestals, concrete pads, fiber optic lines, and all necessary supporting "
    "appurtenances.\n\n"
    "2. Grant of Access and Drainage Easement. Grantor hereby grants to Grantee a "
    "non-exclusive easement for storm water drainage and to construct, operate, inspect, "
    "maintain, repair and replace drainage improvements.\n\n"
    "3. Term. The easement shall commence on the date hereof and terminate upon the later "
    "of (a) termination of the Lease, or (b) completion of decommissioning.\n\n"
    "4. Maintenance. Grantee shall be responsible for maintenance of the Access and Utility "
    "Easement Area.\n\n"
    "5. Covenants Running with the Land. The easement and other rights conferred by this "
    "Agreement are intended to constitute covenants that run with the land.\n\n"
    "6. Indemnity. Each party shall indemnify, defend and hold harmless the other party from "
    "losses caused by the indemnifying party's negligence or willful misconduct.\n\n"
    "7. Governing Law. This Easement Agreement shall be governed by the laws of the State "
    "of California."
)

pdf.ln(10)
for party in [("GRANTOR:", "Mojave Solar Ranch LLC", "Robert J. Caldwell", "Managing Member"),
              ("GRANTEE:", "Desert Bloom Solar LLC", "Victoria Chen", "President")]:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, party[0], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, party[1], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"By: ___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Name: {party[2]}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Title: {party[3]}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

# ======== OUTPUT ========
pdf.output(OUTPUT)
print(f"Created: {OUTPUT}")
print(f"Size: {os.path.getsize(OUTPUT):,} bytes")
print(f"Pages: {pdf.page}")
