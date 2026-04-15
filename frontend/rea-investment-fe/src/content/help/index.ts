import { HelpArticle, FAQItem, GlossaryEntry, HelpCategory, categoryMeta } from './types';
import { gettingStartedArticles } from './articles/getting-started';
import { homeArticles } from './articles/home';
import { acquisitionsArticles } from './articles/acquisitions';
import { projectHubArticles } from './articles/project-hub';
import { dataRoomArticles } from './articles/data-room';
import { oAndMArticles } from './articles/o-and-m';
import { financeArticles } from './articles/finance';
import { tasksArticles } from './articles/tasks';
import { reportsArticles } from './articles/reports';
import { portfolioAdminArticles } from './articles/portfolio-admin';
import { conceptArticles } from './articles/concepts';
import { referenceArticles } from './articles/reference';
import { troubleshootingArticles } from './articles/troubleshooting';
import { faqItems } from './faq';
import { glossaryEntries } from './glossary';

export { categoryMeta };
export type { HelpArticle, FAQItem, GlossaryEntry, HelpCategory };
export { faqItems, glossaryEntries };

export const allArticles: HelpArticle[] = [
  ...gettingStartedArticles,
  ...homeArticles,
  ...acquisitionsArticles,
  ...projectHubArticles,
  ...dataRoomArticles,
  ...oAndMArticles,
  ...financeArticles,
  ...tasksArticles,
  ...reportsArticles,
  ...portfolioAdminArticles,
  ...conceptArticles,
  ...referenceArticles,
  ...troubleshootingArticles
];

export function getArticleBySlug(slug: string): HelpArticle | undefined {
  return allArticles.find(a => a.slug === slug);
}

export function getArticlesByCategory(category: HelpCategory): HelpArticle[] {
  return allArticles.filter(a => a.category === category);
}

export function getRelatedArticles(article: HelpArticle): HelpArticle[] {
  return article.relatedArticles.map(slug => getArticleBySlug(slug)).filter((a): a is HelpArticle => a !== undefined);
}

export function getFAQGroups(): { group: string; items: FAQItem[] }[] {
  const groups = new Map<string, FAQItem[]>();
  for (const item of faqItems) {
    const list = groups.get(item.group) || [];
    list.push(item);
    groups.set(item.group, list);
  }
  return Array.from(groups.entries()).map(([group, items]) => ({ group, items }));
}

interface SearchResult {
  type: 'article' | 'faq' | 'glossary';
  title: string;
  excerpt: string;
  slug: string;
  category?: string;
  tags: string[];
  score: number;
}

function normalizeQuery(query: string): string[] {
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(t => t.length > 1);
}

function scoreMatch(text: string, terms: string[]): number {
  const lower = text.toLowerCase();
  let score = 0;
  for (const term of terms) {
    if (lower.includes(term)) score += 1;
  }
  return score;
}

function extractExcerpt(body: string, terms: string[], maxLen = 160): string {
  const lines = body.split('\n').filter(l => l.trim() && !l.startsWith('#') && !l.startsWith('|'));
  const lower = terms.map(t => t.toLowerCase());
  for (const line of lines) {
    const ll = line.toLowerCase();
    if (lower.some(t => ll.includes(t))) {
      const clean = line.replace(/[*_`#]/g, '').trim();
      return clean.length > maxLen ? clean.slice(0, maxLen) + '...' : clean;
    }
  }
  const first = lines[0]?.replace(/[*_`#]/g, '').trim() || '';
  return first.length > maxLen ? first.slice(0, maxLen) + '...' : first;
}

export function searchHelp(query: string): SearchResult[] {
  const terms = normalizeQuery(query);
  if (terms.length === 0) return [];

  const results: SearchResult[] = [];

  for (const article of allArticles) {
    const titleScore = scoreMatch(article.title, terms) * 5;
    const summaryScore = scoreMatch(article.summary, terms) * 3;
    const tagScore = scoreMatch(article.tags.join(' '), terms) * 3;
    const keywordScore = scoreMatch(article.searchKeywords.join(' '), terms) * 4;
    const bodyScore = scoreMatch(article.body, terms) * 1;
    const total = titleScore + summaryScore + tagScore + keywordScore + bodyScore;
    if (total > 0) {
      results.push({
        type: 'article',
        title: article.title,
        excerpt: extractExcerpt(article.body, terms),
        slug: article.slug,
        category: categoryMeta.find(c => c.id === article.category)?.title || article.category,
        tags: article.tags,
        score: total
      });
    }
  }

  for (const faq of faqItems) {
    const qScore = scoreMatch(faq.question, terms) * 5;
    const aScore = scoreMatch(faq.answer, terms) * 2;
    const tScore = scoreMatch(faq.tags.join(' '), terms) * 3;
    const total = qScore + aScore + tScore;
    if (total > 0) {
      results.push({
        type: 'faq',
        title: faq.question,
        excerpt: faq.answer.length > 160 ? faq.answer.slice(0, 160) + '...' : faq.answer,
        slug: `faq#${faq.id}`,
        category: 'FAQ — ' + faq.group,
        tags: faq.tags,
        score: total
      });
    }
  }

  for (const entry of glossaryEntries) {
    const tScore = scoreMatch(entry.term, terms) * 6;
    const dScore = scoreMatch(entry.definition, terms) * 2;
    const total = tScore + dScore;
    if (total > 0) {
      results.push({
        type: 'glossary',
        title: entry.term,
        excerpt: entry.definition.length > 160 ? entry.definition.slice(0, 160) + '...' : entry.definition,
        slug: `glossary#${entry.slug}`,
        category: 'Glossary',
        tags: entry.tags,
        score: total
      });
    }
  }

  results.sort((a, b) => b.score - a.score);
  return results;
}
