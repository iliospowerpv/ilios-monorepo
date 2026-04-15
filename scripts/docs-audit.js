#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const REGISTRY_PATH = path.resolve(__dirname, '..', 'docs', 'route-help-registry.json');
const COVERAGE_PATH = path.resolve(__dirname, '..', 'docs', 'documentation-coverage.json');
const HELP_CONTENT_DIR = path.resolve(__dirname, '..', 'frontend', 'rea-investment-fe', 'src', 'content', 'help', 'articles');

function loadJSON(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch (err) {
    console.error(`Failed to load ${filePath}: ${err.message}`);
    process.exit(1);
  }
}

function scanContentDirectory(contentDir) {
  const slugs = new Set();
  if (!fs.existsSync(contentDir)) {
    console.warn(`Help content directory not found: ${contentDir}`);
    return slugs;
  }

  const files = fs.readdirSync(contentDir).filter(f => f.endsWith('.ts') || f.endsWith('.js'));
  for (const file of files) {
    const content = fs.readFileSync(path.join(contentDir, file), 'utf-8');
    const slugMatches = content.matchAll(/slug:\s*['"]([^'"]+)['"]/g);
    for (const match of slugMatches) {
      slugs.add(match[1]);
    }
  }
  return slugs;
}

function auditRouteRegistry(registry, contentSlugs) {
  const issues = [];
  const stats = { total: 0, mapped: 0, unmapped: 0, excluded: 0 };
  const routes = registry.routes || {};
  const articles = registry.helpArticles || {};

  for (const [routePath, routeConfig] of Object.entries(routes)) {
    if (routeConfig.excludeFromCoverage) {
      stats.excluded++;
      continue;
    }

    stats.total++;
    const helpArticles = routeConfig.helpArticles || [];

    if (helpArticles.length === 0) {
      stats.unmapped++;
      issues.push({
        type: 'UNMAPPED_ROUTE',
        severity: 'warning',
        route: routePath,
        module: routeConfig.module,
        label: routeConfig.label,
        message: `Route "${routePath}" (${routeConfig.label}) has no help articles mapped`
      });
    } else {
      stats.mapped++;
      for (const articleSlug of helpArticles) {
        if (!articles[articleSlug]) {
          issues.push({
            type: 'MISSING_ARTICLE_IN_REGISTRY',
            severity: 'error',
            route: routePath,
            articleSlug,
            message: `Route "${routePath}" references article "${articleSlug}" which is not defined in helpArticles registry`
          });
        }
      }
    }
  }

  for (const [slug, article] of Object.entries(articles)) {
    if (!contentSlugs.has(slug)) {
      issues.push({
        type: 'ARTICLE_NOT_IN_CONTENT',
        severity: 'error',
        articleSlug: slug,
        message: `Article "${slug}" ("${article.title}") is registered but has no matching content in the help articles directory`
      });
    }
  }

  const orphanedContent = [];
  for (const slug of contentSlugs) {
    if (!articles[slug]) {
      orphanedContent.push(slug);
    }
  }

  const stubArticles = [];
  for (const [slug, article] of Object.entries(articles)) {
    if (article.status === 'stub') {
      stubArticles.push({ slug, title: article.title });
    }
  }

  return { issues, stats, stubArticles, orphanedContent };
}

function auditCoverageInventory(coverage) {
  const issues = [];
  const moduleStats = { total: 0, covered: 0, partial: 0, missing: 0 };
  const pageStats = { total: 0, covered: 0, partial: 0, missing: 0 };
  const modules = coverage.modules || {};

  for (const [moduleKey, moduleConfig] of Object.entries(modules)) {
    moduleStats.total++;
    moduleStats[moduleConfig.status]++;

    if (!moduleConfig.overviewArticle) {
      issues.push({
        type: 'NO_MODULE_OVERVIEW',
        severity: 'warning',
        module: moduleKey,
        label: moduleConfig.label,
        message: `Module "${moduleConfig.label}" has no overview article`
      });
    }

    for (const page of moduleConfig.pages || []) {
      pageStats.total++;
      pageStats[page.status]++;
    }
  }

  return { issues, moduleStats, pageStats };
}

function auditRegistryCoverageParity(registry, coverage) {
  const issues = [];
  const routes = registry.routes || {};

  const registryRoutes = new Set();
  for (const [routePath, routeConfig] of Object.entries(routes)) {
    if (!routeConfig.excludeFromCoverage) {
      registryRoutes.add(routePath);
    }
  }

  const coverageRoutes = new Set();
  const modules = coverage.modules || {};
  for (const moduleConfig of Object.values(modules)) {
    for (const page of moduleConfig.pages || []) {
      coverageRoutes.add(page.route);
    }
  }

  for (const route of registryRoutes) {
    if (!coverageRoutes.has(route)) {
      issues.push({
        type: 'REGISTRY_NOT_IN_COVERAGE',
        severity: 'error',
        route,
        message: `Route "${route}" exists in registry but is missing from coverage inventory`
      });
    }
  }

  for (const route of coverageRoutes) {
    if (!registryRoutes.has(route)) {
      issues.push({
        type: 'COVERAGE_NOT_IN_REGISTRY',
        severity: 'error',
        route,
        message: `Route "${route}" exists in coverage inventory but is missing from registry`
      });
    }
  }

  for (const [moduleKey, moduleConfig] of Object.entries(modules)) {
    for (const page of moduleConfig.pages || []) {
      const registryEntry = routes[page.route];
      if (registryEntry && !registryEntry.excludeFromCoverage) {
        const hasArticles = (registryEntry.helpArticles || []).length > 0;
        if (hasArticles && page.status === 'missing') {
          issues.push({
            type: 'STATUS_MISMATCH',
            severity: 'error',
            route: page.route,
            message: `Route "${page.route}" has help articles in registry but status is "missing" in coverage`
          });
        }
        if (!hasArticles && (page.status === 'covered' || page.status === 'partial')) {
          issues.push({
            type: 'STATUS_MISMATCH',
            severity: 'error',
            route: page.route,
            message: `Route "${page.route}" has no help articles in registry but status is "${page.status}" in coverage`
          });
        }
        if (registryEntry.module !== moduleKey) {
          issues.push({
            type: 'MODULE_MISMATCH',
            severity: 'error',
            route: page.route,
            message: `Route "${page.route}" is in module "${moduleKey}" in coverage but "${registryEntry.module}" in registry`
          });
        }
      }
    }
  }

  return issues;
}

function printReport(registryAudit, coverageAudit, parityIssues) {
  const divider = '='.repeat(70);
  const thinDivider = '-'.repeat(70);

  console.log('');
  console.log(divider);
  console.log('  DOCUMENTATION COVERAGE AUDIT REPORT');
  console.log(divider);
  console.log('');

  console.log('ROUTE-TO-HELP MAPPING SUMMARY');
  console.log(thinDivider);
  const rs = registryAudit.stats;
  const mappedPct = rs.total > 0 ? ((rs.mapped / rs.total) * 100).toFixed(1) : '0.0';
  console.log(`  Total routes:    ${rs.total} (${rs.excluded} excluded: auth/redirects)`);
  console.log(`  Mapped:          ${rs.mapped} (${mappedPct}%)`);
  console.log(`  Unmapped:        ${rs.unmapped}`);
  console.log('');

  console.log('MODULE COVERAGE SUMMARY');
  console.log(thinDivider);
  const ms = coverageAudit.moduleStats;
  console.log(`  Total modules:   ${ms.total}`);
  console.log(`  Covered:         ${ms.covered}`);
  console.log(`  Partial:         ${ms.partial}`);
  console.log(`  Missing:         ${ms.missing}`);
  console.log('');

  console.log('PAGE COVERAGE SUMMARY');
  console.log(thinDivider);
  const ps = coverageAudit.pageStats;
  const coveredPct = ps.total > 0 ? (((ps.covered + ps.partial) / ps.total) * 100).toFixed(1) : '0.0';
  console.log(`  Total pages:     ${ps.total}`);
  console.log(`  Covered:         ${ps.covered}`);
  console.log(`  Partial:         ${ps.partial}`);
  console.log(`  Missing:         ${ps.missing}`);
  console.log(`  Coverage:        ${coveredPct}% (covered + partial)`);
  console.log('');

  const allIssues = [...registryAudit.issues, ...coverageAudit.issues, ...parityIssues];
  const errors = allIssues.filter(i => i.severity === 'error');
  const warnings = allIssues.filter(i => i.severity === 'warning');

  if (errors.length > 0) {
    console.log('ERRORS');
    console.log(thinDivider);
    for (const issue of errors) {
      console.log(`  [ERROR] ${issue.message}`);
    }
    console.log('');
  }

  if (warnings.length > 0) {
    const unmapped = warnings.filter(w => w.type === 'UNMAPPED_ROUTE');
    const noOverview = warnings.filter(w => w.type === 'NO_MODULE_OVERVIEW');

    if (unmapped.length > 0) {
      console.log('WARNINGS - Unmapped Routes');
      console.log(thinDivider);
      for (const issue of unmapped) {
        console.log(`  [WARN] ${issue.message}`);
      }
      console.log('');
    }

    if (noOverview.length > 0) {
      console.log('WARNINGS - Modules Without Overview Articles');
      console.log(thinDivider);
      for (const issue of noOverview) {
        console.log(`  [WARN] ${issue.message}`);
      }
      console.log('');
    }
  }

  if (registryAudit.stubArticles.length > 0) {
    console.log('STUB ARTICLES (content not yet written)');
    console.log(thinDivider);
    for (const article of registryAudit.stubArticles) {
      console.log(`  [STUB] ${article.slug} - "${article.title}"`);
    }
    console.log('');
  }

  if (registryAudit.orphanedContent.length > 0) {
    console.log('INFO - Content slugs not referenced in registry');
    console.log(thinDivider);
    for (const slug of registryAudit.orphanedContent) {
      console.log(`  [INFO] "${slug}" exists in content directory but is not in the helpArticles registry`);
    }
    console.log('');
  }

  console.log(divider);
  const overallScore = rs.total > 0 ? ((rs.mapped / rs.total) * 100).toFixed(1) : '0.0';
  console.log(`  OVERALL ROUTE COVERAGE: ${overallScore}%`);
  console.log(`  ISSUES: ${errors.length} errors, ${warnings.length} warnings`);
  console.log(divider);
  console.log('');

  if (errors.length > 0) {
    process.exit(1);
  }
}

function main() {
  console.log('Loading route-help registry...');
  const registry = loadJSON(REGISTRY_PATH);

  console.log('Loading documentation coverage inventory...');
  const coverage = loadJSON(COVERAGE_PATH);

  const helpContentDir = registry.helpContentDir
    ? path.resolve(__dirname, '..', registry.helpContentDir)
    : HELP_CONTENT_DIR;

  console.log(`Scanning help content directory: ${helpContentDir}`);
  const contentSlugs = scanContentDirectory(helpContentDir);
  console.log(`Found ${contentSlugs.size} article slugs in content directory`);
  console.log('');

  const registryAudit = auditRouteRegistry(registry, contentSlugs);
  const coverageAudit = auditCoverageInventory(coverage);
  const parityIssues = auditRegistryCoverageParity(registry, coverage);

  printReport(registryAudit, coverageAudit, parityIssues);
}

main();
