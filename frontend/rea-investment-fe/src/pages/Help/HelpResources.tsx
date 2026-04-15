import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Chip from '@mui/material/Chip';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Divider from '@mui/material/Divider';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SearchIcon from '@mui/icons-material/Search';
import RocketLaunchOutlinedIcon from '@mui/icons-material/RocketLaunchOutlined';
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AccountBalanceOutlinedIcon from '@mui/icons-material/AccountBalanceOutlined';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import WhatshotOutlinedIcon from '@mui/icons-material/WhatshotOutlined';
import AccountBalanceWalletOutlinedIcon from '@mui/icons-material/AccountBalanceWalletOutlined';
import AssignmentTurnedInOutlinedIcon from '@mui/icons-material/AssignmentTurnedInOutlined';
import AssessmentOutlinedIcon from '@mui/icons-material/AssessmentOutlined';
import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined';
import LightbulbOutlinedIcon from '@mui/icons-material/LightbulbOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import BuildOutlinedIcon from '@mui/icons-material/BuildOutlined';
import QuestionAnswerOutlinedIcon from '@mui/icons-material/QuestionAnswerOutlined';
import AbcIcon from '@mui/icons-material/Abc';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import {
  allArticles,
  searchHelp,
  getArticlesByCategory,
  categoryMeta,
  faqItems,
  glossaryEntries,
  getFAQGroups,
  HelpCategory
} from '../../content/help';

const iconMap: Record<string, React.ReactNode> = {
  RocketLaunch: <RocketLaunchOutlinedIcon />,
  Home: <HomeOutlinedIcon />,
  TrendingUp: <TrendingUpIcon />,
  AccountBalance: <AccountBalanceOutlinedIcon />,
  Folder: <FolderOutlinedIcon />,
  Whatshot: <WhatshotOutlinedIcon />,
  AccountBalanceWallet: <AccountBalanceWalletOutlinedIcon />,
  AssignmentTurnedIn: <AssignmentTurnedInOutlinedIcon />,
  Assessment: <AssessmentOutlinedIcon />,
  AdminPanelSettings: <AdminPanelSettingsOutlinedIcon />,
  Lightbulb: <LightbulbOutlinedIcon />,
  MenuBook: <MenuBookOutlinedIcon />,
  Build: <BuildOutlinedIcon />,
  QuestionAnswer: <QuestionAnswerOutlinedIcon />,
  Abc: <AbcIcon />
};

const HelpResources: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const viewParam = searchParams.get('view');
  const categoryParam = searchParams.get('category') as HelpCategory | null;
  const articleParam = searchParams.get('article');
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [activeSearch, setActiveSearch] = useState(searchParams.get('q') || '');

  const searchResults = useMemo(() => {
    if (!activeSearch.trim()) return [];
    return searchHelp(activeSearch);
  }, [activeSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(searchQuery);
    if (searchQuery.trim()) {
      setSearchParams({ q: searchQuery });
    } else {
      setSearchParams({});
    }
  };

  const handleCategoryClick = (catId: HelpCategory) => {
    if (catId === 'faq') {
      setSearchParams({ view: 'faq' });
    } else if (catId === 'glossary') {
      setSearchParams({ view: 'glossary' });
    } else {
      setSearchParams({ category: catId });
    }
    setActiveSearch('');
    setSearchQuery('');
  };

  const handleArticleClick = (slug: string) => {
    setSearchParams({ article: slug });
    setActiveSearch('');
    setSearchQuery('');
  };

  const handleBackToHome = () => {
    setSearchParams({});
    setActiveSearch('');
    setSearchQuery('');
  };

  const currentArticle = useMemo(() => {
    if (!articleParam) return null;
    return allArticles.find(a => a.slug === articleParam) || null;
  }, [articleParam]);

  const relatedArticles = useMemo(() => {
    if (!currentArticle) return [];
    return currentArticle.relatedArticles
      .map(slug => allArticles.find(a => a.slug === slug))
      .filter((a): a is (typeof allArticles)[0] => !!a);
  }, [currentArticle]);

  const categoryArticles = useMemo(() => {
    if (!categoryParam) return [];
    return getArticlesByCategory(categoryParam);
  }, [categoryParam]);

  const currentCategory = useMemo(() => {
    if (categoryParam) return categoryMeta.find(c => c.id === categoryParam);
    if (currentArticle) return categoryMeta.find(c => c.id === currentArticle.category);
    return null;
  }, [categoryParam, currentArticle]);

  const isHome = !viewParam && !categoryParam && !articleParam && !activeSearch.trim();
  const isSearch = !!activeSearch.trim();
  const isCategoryView = !!categoryParam && !articleParam;
  const isArticleView = !!currentArticle;
  const isFAQView = viewParam === 'faq';
  const isGlossaryView = viewParam === 'glossary';
  const faqItemParam = searchParams.get('item');
  const glossaryTermParam = searchParams.get('term');
  const [expandedFaqId, setExpandedFaqId] = useState<string | null>(faqItemParam);

  useEffect(() => {
    if (isFAQView && faqItemParam) {
      setExpandedFaqId(faqItemParam);
      setTimeout(() => {
        document.getElementById(faqItemParam)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
    if (isGlossaryView && glossaryTermParam) {
      setTimeout(() => {
        document.getElementById(glossaryTermParam)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [isFAQView, isGlossaryView, faqItemParam, glossaryTermParam]);

  const renderBreadcrumbs = () => {
    const crumbs: { label: string; onClick?: () => void }[] = [
      { label: 'Help & Resources', onClick: handleBackToHome }
    ];
    if (currentCategory) {
      crumbs.push({
        label: currentCategory.title,
        onClick: () => handleCategoryClick(currentCategory.id)
      });
    }
    if (isFAQView) crumbs.push({ label: 'FAQs' });
    if (isGlossaryView) crumbs.push({ label: 'Glossary' });
    if (currentArticle) crumbs.push({ label: currentArticle.title });
    if (isSearch) crumbs.push({ label: `Search: "${activeSearch}"` });

    return (
      <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 2, flexWrap: 'wrap' }}>
        {crumbs.map((crumb, i) => (
          <React.Fragment key={i}>
            {i > 0 && <ChevronRightIcon fontSize="small" sx={{ color: 'text.disabled', mx: 0.5 }} />}
            {crumb.onClick && i < crumbs.length - 1 ? (
              <Typography
                variant="body2"
                sx={{ color: 'primary.main', cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                onClick={crumb.onClick}
              >
                {crumb.label}
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary">
                {crumb.label}
              </Typography>
            )}
          </React.Fragment>
        ))}
      </Stack>
    );
  };

  const renderSearchBar = () => (
    <Box component="form" onSubmit={handleSearch} sx={{ mb: 4 }}>
      <TextField
        fullWidth
        placeholder="Search help articles, FAQs, and glossary..."
        value={searchQuery}
        onChange={e => setSearchQuery(e.target.value)}
        size="small"
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon color="action" />
            </InputAdornment>
          )
        }}
      />
    </Box>
  );

  const renderCategoryGrid = () => (
    <Grid container spacing={2}>
      {categoryMeta.map(cat => {
        const articles = getArticlesByCategory(cat.id);
        const count =
          cat.id === 'faq' ? faqItems.length : cat.id === 'glossary' ? glossaryEntries.length : articles.length;
        return (
          <Grid item xs={12} sm={6} md={4} key={cat.id}>
            <Paper
              elevation={0}
              sx={{
                border: 1,
                borderColor: 'divider',
                p: 2.5,
                height: '100%',
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' }
              }}
              onClick={() => handleCategoryClick(cat.id)}
            >
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
                <Box sx={{ color: 'primary.main' }}>{iconMap[cat.icon]}</Box>
                <Typography variant="subtitle1" fontWeight={600}>
                  {cat.title}
                </Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {cat.description}
              </Typography>
              <Typography variant="caption" color="text.disabled">
                {count} {cat.id === 'faq' ? 'questions' : cat.id === 'glossary' ? 'terms' : 'articles'}
              </Typography>
            </Paper>
          </Grid>
        );
      })}
    </Grid>
  );

  const renderSearchResults = () => (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for &ldquo;{activeSearch}&rdquo;
      </Typography>
      {searchResults.length === 0 ? (
        <Paper elevation={0} sx={{ border: 1, borderColor: 'divider', p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No results found. Try different keywords or browse the categories below.
          </Typography>
        </Paper>
      ) : (
        <Stack spacing={1.5}>
          {searchResults.map((result, i) => (
            <Paper
              key={i}
              elevation={0}
              sx={{
                border: 1,
                borderColor: 'divider',
                p: 2,
                cursor: 'pointer',
                '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' }
              }}
              onClick={() => {
                if (result.type === 'article') {
                  handleArticleClick(result.slug);
                } else if (result.type === 'faq') {
                  const faqId = result.slug.replace('faq#', '');
                  setSearchParams({ view: 'faq', item: faqId });
                  setActiveSearch('');
                  setSearchQuery('');
                } else {
                  const termSlug = result.slug.replace('glossary#', '');
                  setSearchParams({ view: 'glossary', term: termSlug });
                  setActiveSearch('');
                  setSearchQuery('');
                }
              }}
            >
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
                <Chip
                  label={result.type === 'article' ? 'Article' : result.type === 'faq' ? 'FAQ' : 'Glossary'}
                  size="small"
                  variant="outlined"
                  color={result.type === 'article' ? 'primary' : result.type === 'faq' ? 'info' : 'default'}
                />
                {result.category && (
                  <Typography variant="caption" color="text.disabled">
                    {result.category}
                  </Typography>
                )}
              </Stack>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                {result.title}
              </Typography>
              {result.tags.length > 0 && (
                <Stack direction="row" spacing={0.5} sx={{ mb: 0.5, flexWrap: 'wrap' }}>
                  {result.tags.map(tag => (
                    <Chip
                      key={tag}
                      label={tag.replace(/-/g, ' ')}
                      size="small"
                      variant="filled"
                      sx={{ fontSize: '0.7rem', height: 20 }}
                    />
                  ))}
                </Stack>
              )}
              <Typography variant="body2" color="text.secondary">
                {result.excerpt}
              </Typography>
            </Paper>
          ))}
        </Stack>
      )}
    </Box>
  );

  const renderCategoryView = () => {
    if (!currentCategory) return null;
    return (
      <Box>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
          <Box sx={{ color: 'primary.main' }}>{iconMap[currentCategory.icon]}</Box>
          <Typography variant="h5" fontWeight={600}>
            {currentCategory.title}
          </Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {currentCategory.description}
        </Typography>
        <List disablePadding>
          {categoryArticles.map((article, i) => (
            <ListItem key={article.slug} disablePadding divider={i < categoryArticles.length - 1}>
              <ListItemButton onClick={() => handleArticleClick(article.slug)} sx={{ py: 1.5 }}>
                <ArticleOutlinedIcon fontSize="small" sx={{ mr: 2, color: 'action.active' }} />
                <ListItemText
                  primary={article.title}
                  secondary={article.summary}
                  primaryTypographyProps={{ fontWeight: 500 }}
                  secondaryTypographyProps={{ variant: 'body2' }}
                />
                <Stack direction="row" spacing={0.5} sx={{ ml: 1, flexShrink: 0 }}>
                  <Chip label={article.articleType} size="small" variant="outlined" />
                </Stack>
                <ChevronRightIcon color="action" sx={{ ml: 1 }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    );
  };

  const renderArticleBody = (body: string) => {
    const lines = body.split('\n');
    const elements: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];
    let tableHeaders: string[] = [];

    const flushTable = () => {
      if (tableHeaders.length > 0) {
        elements.push(
          <Box key={`table-${elements.length}`} sx={{ overflowX: 'auto', my: 2 }}>
            <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr>
                  {tableHeaders.map((h, i) => (
                    <Box
                      component="th"
                      key={i}
                      sx={{ p: 1, borderBottom: 2, borderColor: 'divider', textAlign: 'left', fontWeight: 600 }}
                    >
                      {h}
                    </Box>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <Box component="td" key={ci} sx={{ p: 1, borderBottom: 1, borderColor: 'divider' }}>
                        {formatInlineText(cell)}
                      </Box>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Box>
          </Box>
        );
      }
      tableHeaders = [];
      tableRows = [];
      inTable = false;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.startsWith('|') && line.endsWith('|')) {
        const cells = line
          .split('|')
          .slice(1, -1)
          .map(c => c.trim());
        if (!inTable) {
          inTable = true;
          tableHeaders = cells;
        } else if (cells.every(c => /^[-:]+$/.test(c))) {
          continue;
        } else {
          tableRows.push(cells);
        }
        continue;
      } else if (inTable) {
        flushTable();
      }

      if (line.startsWith('## ')) {
        elements.push(
          <Typography
            key={i}
            variant="h5"
            fontWeight={600}
            sx={{ mt: 3, mb: 1.5 }}
            id={line
              .replace(/^## /, '')
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, '-')}
          >
            {line.replace(/^## /, '')}
          </Typography>
        );
      } else if (line.startsWith('### ')) {
        elements.push(
          <Typography key={i} variant="h6" fontWeight={600} sx={{ mt: 2.5, mb: 1 }}>
            {line.replace(/^### /, '')}
          </Typography>
        );
      } else if (line.startsWith('```')) {
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        elements.push(
          <Box
            key={`code-${i}`}
            sx={{
              bgcolor: 'action.hover',
              borderRadius: 1,
              p: 2,
              my: 1.5,
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              overflowX: 'auto',
              whiteSpace: 'pre'
            }}
          >
            {codeLines.join('\n')}
          </Box>
        );
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        const listItems: string[] = [line.replace(/^[-*] /, '')];
        while (i + 1 < lines.length && (lines[i + 1].startsWith('- ') || lines[i + 1].startsWith('* '))) {
          i++;
          listItems.push(lines[i].replace(/^[-*] /, ''));
        }
        elements.push(
          <Box component="ul" key={`ul-${i}`} sx={{ pl: 3, my: 1 }}>
            {listItems.map((item, j) => (
              <Box component="li" key={j} sx={{ mb: 0.5 }}>
                <Typography variant="body1">{formatInlineText(item)}</Typography>
              </Box>
            ))}
          </Box>
        );
      } else if (/^\d+\. /.test(line)) {
        const listItems: string[] = [line.replace(/^\d+\. /, '')];
        while (i + 1 < lines.length && /^\d+\. /.test(lines[i + 1])) {
          i++;
          listItems.push(lines[i].replace(/^\d+\. /, ''));
        }
        elements.push(
          <Box component="ol" key={`ol-${i}`} sx={{ pl: 3, my: 1 }}>
            {listItems.map((item, j) => (
              <Box component="li" key={j} sx={{ mb: 0.5 }}>
                <Typography variant="body1">{formatInlineText(item)}</Typography>
              </Box>
            ))}
          </Box>
        );
      } else if (line.startsWith('`') && line.endsWith('`') && line.length > 2) {
        elements.push(
          <Box
            key={i}
            sx={{
              bgcolor: 'action.hover',
              borderRadius: 1,
              p: 1.5,
              my: 1,
              fontFamily: 'monospace',
              fontSize: '0.85rem'
            }}
          >
            {line.slice(1, -1)}
          </Box>
        );
      } else if (line.trim() === '') {
        continue;
      } else {
        elements.push(
          <Typography key={i} variant="body1" sx={{ mb: 1.5, lineHeight: 1.7 }}>
            {formatInlineText(line)}
          </Typography>
        );
      }
    }
    if (inTable) flushTable();
    return <>{elements}</>;
  };

  const formatInlineText = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let key = 0;

    while (remaining.length > 0) {
      const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
      const codeMatch = remaining.match(/`(.+?)`/);

      type MatchCandidate = { index: number; length: number; node: React.ReactNode };
      const candidates: MatchCandidate[] = [];

      if (boldMatch && boldMatch.index !== undefined) {
        candidates.push({
          index: boldMatch.index,
          length: boldMatch[0].length,
          node: <strong key={key++}>{boldMatch[1]}</strong>
        });
      }
      if (codeMatch && codeMatch.index !== undefined) {
        candidates.push({
          index: codeMatch.index,
          length: codeMatch[0].length,
          node: (
            <Box
              component="code"
              key={key++}
              sx={{ bgcolor: 'action.hover', px: 0.5, borderRadius: 0.5, fontFamily: 'monospace', fontSize: '0.85em' }}
            >
              {codeMatch[1]}
            </Box>
          )
        });
      }

      candidates.sort((a, b) => a.index - b.index);
      const firstMatch = candidates.length > 0 ? candidates[0] : null;

      if (firstMatch) {
        if (firstMatch.index > 0) {
          parts.push(remaining.slice(0, firstMatch.index));
        }
        parts.push(firstMatch.node);
        remaining = remaining.slice(firstMatch.index + firstMatch.length);
      } else {
        parts.push(remaining);
        remaining = '';
      }
    }

    return parts.length === 1 ? parts[0] : <>{parts}</>;
  };

  const renderArticleTOC = (body: string) => {
    const headings = body
      .split('\n')
      .filter(l => l.startsWith('## '))
      .map(l => l.replace(/^## /, ''));
    if (headings.length < 2) return null;
    return (
      <Paper elevation={0} sx={{ border: 1, borderColor: 'divider', p: 2, mb: 3 }}>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          On this page
        </Typography>
        <List disablePadding dense>
          {headings.map((h, i) => (
            <ListItem key={i} disablePadding>
              <ListItemButton
                sx={{ py: 0.25, px: 1 }}
                onClick={() => {
                  const id = h.toLowerCase().replace(/[^a-z0-9]+/g, '-');
                  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                <ListItemText primary={h} primaryTypographyProps={{ variant: 'body2' }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Paper>
    );
  };

  const renderArticleView = () => {
    if (!currentArticle) return null;
    return (
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Typography variant="h4" fontWeight={600} sx={{ mb: 1 }}>
            {currentArticle.title}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Chip label={currentArticle.articleType} size="small" variant="outlined" color="primary" />
            {currentArticle.audience.map(a => (
              <Chip key={a} label={a.replace(/-/g, ' ')} size="small" variant="outlined" />
            ))}
          </Stack>
          <Typography variant="caption" color="text.disabled" sx={{ mb: 3, display: 'block' }}>
            Last updated: {currentArticle.lastUpdated}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3, fontStyle: 'italic' }}>
            {currentArticle.summary}
          </Typography>
          <Divider sx={{ mb: 3 }} />
          {renderArticleBody(currentArticle.body)}
        </Grid>
        <Grid item xs={12} md={4}>
          {renderArticleTOC(currentArticle.body)}
          {relatedArticles.length > 0 && (
            <Paper elevation={0} sx={{ border: 1, borderColor: 'divider', p: 2 }}>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                Related articles
              </Typography>
              <List disablePadding dense>
                {relatedArticles.map(ra => (
                  <ListItem key={ra.slug} disablePadding>
                    <ListItemButton sx={{ py: 0.5, px: 1 }} onClick={() => handleArticleClick(ra.slug)}>
                      <ArticleOutlinedIcon fontSize="small" sx={{ mr: 1, color: 'action.active' }} />
                      <ListItemText primary={ra.title} primaryTypographyProps={{ variant: 'body2' }} />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Paper>
          )}
        </Grid>
      </Grid>
    );
  };

  const renderFAQView = () => {
    const groups = getFAQGroups();
    return (
      <Box>
        <Typography variant="h5" fontWeight={600} sx={{ mb: 1 }}>
          Frequently Asked Questions
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Find answers to common questions about the Ilios platform.
        </Typography>
        {groups.map(group => (
          <Box key={group.group} sx={{ mb: 3 }}>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
              {group.group}
            </Typography>
            {group.items.map(item => (
              <Accordion
                key={item.id}
                id={item.id}
                expanded={expandedFaqId === item.id}
                onChange={(_, isExpanded) => setExpandedFaqId(isExpanded ? item.id : null)}
                elevation={0}
                sx={{ border: 1, borderColor: 'divider', '&:before': { display: 'none' }, mb: 1 }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography fontWeight={500}>{item.question}</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                    {item.answer}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        ))}
      </Box>
    );
  };

  const renderGlossaryView = () => {
    const sorted = [...glossaryEntries].sort((a, b) => a.term.localeCompare(b.term));
    const letters = Array.from(new Set(sorted.map(e => e.term[0].toUpperCase())));
    return (
      <Box>
        <Typography variant="h5" fontWeight={600} sx={{ mb: 1 }}>
          Glossary
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Definitions of key terms used throughout the Ilios platform.
        </Typography>
        <Stack direction="row" spacing={0.5} sx={{ mb: 3, flexWrap: 'wrap' }}>
          {letters.map(l => (
            <Chip
              key={l}
              label={l}
              size="small"
              variant="outlined"
              clickable
              onClick={() => document.getElementById(`glossary-${l}`)?.scrollIntoView({ behavior: 'smooth' })}
            />
          ))}
        </Stack>
        {letters.map(letter => (
          <Box key={letter} id={`glossary-${letter}`} sx={{ mb: 3 }}>
            <Typography variant="h6" fontWeight={600} color="primary" sx={{ mb: 1 }}>
              {letter}
            </Typography>
            {sorted
              .filter(e => e.term[0].toUpperCase() === letter)
              .map(entry => (
                <Box key={entry.slug} id={entry.slug} sx={{ mb: 2, pl: 2 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {entry.term}
                  </Typography>
                  <Typography variant="body1" color="text.secondary" sx={{ mb: 0.5 }}>
                    {entry.definition}
                  </Typography>
                  {entry.relatedTerms.length > 0 && (
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <Typography variant="caption" color="text.disabled">
                        Related:
                      </Typography>
                      {entry.relatedTerms.map(rt => (
                        <Chip key={rt} label={rt} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                      ))}
                    </Stack>
                  )}
                </Box>
              ))}
          </Box>
        ))}
      </Box>
    );
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
        <IconButton
          onClick={() => {
            if (isHome) {
              navigate(-1);
            } else {
              handleBackToHome();
            }
          }}
          size="small"
        >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          Help & Resources
        </Typography>
      </Stack>

      {!isHome && renderBreadcrumbs()}

      {isHome && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Guides, FAQs, and walkthroughs for using the Ilios platform.
        </Typography>
      )}

      {renderSearchBar()}

      {isSearch && renderSearchResults()}
      {isHome && renderCategoryGrid()}
      {isCategoryView && renderCategoryView()}
      {isArticleView && renderArticleView()}
      {isFAQView && renderFAQView()}
      {isGlossaryView && renderGlossaryView()}
    </Box>
  );
};

export default HelpResources;
