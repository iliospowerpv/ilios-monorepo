import { HelpArticle } from '../types';

export const dataRoomArticles: HelpArticle[] = [
  {
    slug: 'data-room-overview',
    title: 'Data Room Overview',
    summary:
      'Secure document management and due diligence workflows for organizing, sharing, and tracking project documents.',
    category: 'data-room',
    module: 'data-room',
    audience: ['all-users'],
    articleType: 'overview',
    tags: ['data-room', 'documents', 'due-diligence', 'files'],
    searchKeywords: ['data room', 'documents', 'files', 'upload', 'due diligence', 'diligence', 'document management'],
    relatedArticles: ['data-room-workflows', 'diligence-workflows-explained', 'data-room-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## What Is the Data Room?

The **Data Room** is Ilios's document management system, accessible as a tab within the Project Hub. It provides a secure, organized space for storing and managing all documents related to a project.

## Key Features

### Document Categories
Documents are organized into predefined categories that align with due diligence requirements:
- Legal documents
- Financial records
- Environmental reports
- Engineering studies
- Permits and approvals
- Insurance certificates
- Contracts and agreements

### Document Upload and Management
- Upload individual files or bulk upload multiple documents
- Assign documents to categories
- Track document versions
- Set document status (draft, review, final)

### Due Diligence Tracking
- Track completion status of required document categories
- Monitor overall due diligence readiness
- Identify missing or incomplete document sets

### Access Control
- Document access follows project-level permissions
- Sensitive documents can have additional access restrictions

## Who Uses It

- **Due Diligence teams** — Upload and organize documents during acquisition
- **Legal teams** — Review contracts and compliance documents
- **Asset Managers** — Maintain ongoing project documentation
- **Finance teams** — Access financial records and projections

## Important Terms

- **Category** — A classification for organizing documents (e.g., Legal, Financial)
- **Due Diligence** — The process of verifying project information before acquisition
- **Data Room** — A secure space for organizing and sharing project documents`
  },
  {
    slug: 'data-room-workflows',
    title: 'Data Room Workflows',
    summary: 'How to upload, organize, and manage documents in the Data Room.',
    category: 'data-room',
    module: 'data-room',
    audience: ['all-users'],
    articleType: 'tutorial',
    tags: ['data-room', 'workflow', 'upload', 'documents'],
    searchKeywords: ['upload document', 'add file', 'organize document', 'document category', 'manage files'],
    relatedArticles: ['data-room-overview', 'data-room-key-screens', 'troubleshooting-uploads'],
    lastUpdated: '2026-04-01',
    body: `## Uploading Documents

1. Navigate to the project in **Project Hub**
2. Select the **Data Room** tab
3. Choose the appropriate category for your document
4. Click **Upload** or drag and drop files
5. Add metadata (title, description, tags) as needed
6. Click **Save** to complete the upload

## Organizing Documents

### Assigning Categories
Each document should be placed in the appropriate category:
- Select the document
- Choose "Move" or "Recategorize"
- Select the target category

### Searching for Documents
Use the search functionality within the Data Room to find documents by:
- File name
- Category
- Upload date
- Tags

## Reviewing Due Diligence Status

1. Open the Data Room for a project
2. Review the category completion indicators
3. Categories with missing documents will show incomplete status
4. Upload missing documents to advance due diligence readiness

## Document Version Management

When updating an existing document:
1. Navigate to the document
2. Upload the new version
3. The previous version is preserved in version history
4. Add a note explaining what changed`
  },
  {
    slug: 'data-room-key-screens',
    title: 'Data Room Key Screens',
    summary: 'Overview of the main Data Room interface and its components.',
    category: 'data-room',
    module: 'data-room',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['data-room', 'screens', 'interface'],
    searchKeywords: ['data room screen', 'document list', 'category view', 'file browser'],
    relatedArticles: ['data-room-overview', 'data-room-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Category View

The main Data Room interface shows:
- **Category list** — All document categories with completion status
- **Document count** — Number of documents in each category
- **Status indicators** — Visual cues for complete/incomplete categories

## Document List

Within each category:
- **File listing** — All documents with name, type, upload date
- **Actions** — Download, preview, delete, move options
- **Metadata** — Document details and version information

## Upload Interface

The upload dialog provides:
- **Drag and drop zone** — Drop files directly
- **File browser** — Select files from your computer
- **Category selector** — Assign the upload to a category
- **Metadata fields** — Title, description, and tags

## Document Preview

Click on a document to:
- View supported file types directly in the browser
- See document metadata and version history
- Access download and sharing options`
  },
  {
    slug: 'data-room-troubleshooting',
    title: 'Data Room Troubleshooting',
    summary: 'Solutions for common Data Room issues including upload problems and missing documents.',
    category: 'data-room',
    module: 'data-room',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['data-room', 'troubleshooting', 'upload', 'documents'],
    searchKeywords: ['upload failed', 'document missing', 'cannot upload', 'file not showing', 'data room problem'],
    relatedArticles: ['data-room-overview', 'troubleshooting-uploads', 'troubleshooting-permissions'],
    lastUpdated: '2026-04-01',
    body: `## Upload Fails or Times Out

**Possible causes:**
- File size exceeds the maximum limit
- Network connectivity issues
- Unsupported file format

**Solution:** Check the file size (typically limited to 100MB per file). Ensure you have a stable internet connection. Try a different file format if the type is not supported.

## Documents Not Appearing After Upload

**Possible causes:**
- The upload may not have completed successfully
- You may be looking in the wrong category
- Browser cache may be showing stale data

**Solution:** Refresh the page and check the correct category. If the document still doesn't appear, try uploading again.

## Cannot Delete or Move Documents

**Cause:** You may not have edit permissions for the Data Room.

**Solution:** Contact your administrator to verify your permissions include Data Room edit access.

## Due Diligence Status Not Updating

**Cause:** Status calculations may refresh on a schedule rather than immediately.

**Solution:** Refresh the page. If the status still doesn't reflect your recent uploads, wait a few minutes and check again.`
  },
  {
    slug: 'assumptions-reconciliation',
    title: 'Assumptions Reconciliation (Read-Only)',
    summary:
      'A read-only admin view that traces each diligence field from AI extraction through to the active baseline.',
    category: 'data-room',
    module: 'project-hub',
    audience: ['admin', 'asset-manager'],
    articleType: 'reference',
    tags: ['due diligence', 'reconciliation', 'baseline', 'assumptions', 'admin'],
    searchKeywords: [
      'assumptions reconciliation',
      'reconciliation tab',
      'reconciliation view',
      'active fact',
      'draft baseline',
      'active baseline',
      'legacy value',
      'readiness'
    ],
    relatedArticles: ['assumptions-reconciliation-explained', 'data-room-overview'],
    lastUpdated: '2026-06-12',
    body: `## Where to Find It

The **Reconciliation** tab appears on a project's detail page (Project Hub → a project → **Reconciliation**) for administrators and users with Diligence access. If you don't have permission, the tab is hidden and opening its link directly shows an access-restricted message.

## What It Shows

The view is strictly **read-only**. It does not let you edit, accept, promote, or activate anything — it only reports the current state. For each diligence field it shows:

- The value at every stage: **AI value → Accepted → Active fact → Draft baseline → Active baseline**, plus the **Legacy** value for comparison.
- A **status** chip (Missing, Candidate only, Active fact, In draft baseline, In active baseline).
- **Warnings** when values diverge or a required value is missing.
- **Provenance** — the source document type, page, AI confidence, and a short evidence snippet (shown as text in this release).

A **Baseline Readiness** summary at the top indicates whether the project can form a weather-adjusted draft baseline, whether an active baseline exists, and whether design-estimate monthly points are complete.

## Reading the View

- Group rows by **category** and filter by **status**, by category, by free text, or to **only rows with warnings**.
- Remember that **AI value ≠ truth**, **accepted ≠ active**, **draft ≠ active baseline**, and a **design estimate** is not the same as a **weather-adjusted baseline**. Legacy values are shown for context only and are never used to build a V2 baseline.

For a deeper explanation of these concepts, see **Assumptions Reconciliation Explained**.`
  }
];
