import * as React from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import { usePrevious } from '../../../../hooks/common/usePrevious';

import type { CompanySites } from '../../../../api';

interface SelectedItemsDisplayRendererProps {
  dropdownOpen: boolean;
  displayFocused: boolean;
  selectedCompaniesSites: CompanySites[];
  handleSiteUnselect: (companyId: number, siteId: number) => void;
}

export const SelectedItemsDisplayRenderer: React.FC<SelectedItemsDisplayRendererProps> = ({
  dropdownOpen,
  displayFocused,
  selectedCompaniesSites,
  handleSiteUnselect
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = React.useState<number>(0);
  const previousContainerWidth = usePrevious(containerWidth);
  const [itemsToShowCount, setItemsToShowCount] = React.useState(0);

  React.useEffect(() => {
    const observer = new ResizeObserver(entries => {
      const [entry] = entries;
      setContainerWidth(entry.borderBoxSize[0].inlineSize);
    });

    containerRef.current && observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  React.useEffect(() => {
    if (containerRef.current && !(dropdownOpen || displayFocused)) {
      const childrenNodeList = Array.from(containerRef.current.children);

      let leftoverWidth = containerWidth;
      let itemsToShow = 0;
      if (!previousContainerWidth || previousContainerWidth > containerWidth) {
        for (const childNode of childrenNodeList) {
          if (childNode instanceof HTMLElement && leftoverWidth >= childNode.offsetWidth + 4) {
            leftoverWidth -= childNode.offsetWidth + 4;
            itemsToShow++;
          } else {
            break;
          }
        }
      } else {
        let prevLeftoverWidth = leftoverWidth;
        const avgItemWidth =
          childrenNodeList.reduce(
            (inTotal, childNode) => (childNode instanceof HTMLElement ? childNode.offsetWidth + inTotal : inTotal),
            0
          ) / childrenNodeList.length;

        do {
          prevLeftoverWidth = leftoverWidth;
          leftoverWidth -= avgItemWidth + 4;
          itemsToShow++;
        } while (leftoverWidth > avgItemWidth && leftoverWidth > 0 && prevLeftoverWidth - leftoverWidth > 15);
      }

      setItemsToShowCount(itemsToShow);
      return;
    }
    setItemsToShowCount(0);
  }, [containerWidth, selectedCompaniesSites, dropdownOpen, displayFocused, previousContainerWidth]);

  const items = selectedCompaniesSites
    .map(({ id: companyId, sites }) => sites.map(siteData => ({ ...siteData, companyId })))
    .flat();

  const hiddenCount = dropdownOpen || displayFocused || !itemsToShowCount ? 0 : items.length - itemsToShowCount;
  const itemsToShow =
    dropdownOpen || displayFocused || !itemsToShowCount
      ? items
      : items.slice(0, hiddenCount > 0 ? itemsToShowCount - 1 : itemsToShowCount);

  return (
    <Box
      ref={containerRef}
      sx={{
        width: '100%',
        display: 'flex',
        flexWrap: dropdownOpen || displayFocused ? 'wrap' : 'nowrap',
        overflow: 'hidden',
        gap: 0.5,
        pt: 0.5
      }}
    >
      {itemsToShow.map(site => (
        <Chip
          sx={{ visibility: dropdownOpen || displayFocused || itemsToShowCount ? 'visible' : 'hidden' }}
          size="small"
          variant="outlined"
          key={`${site.companyId}.${site.id}`}
          label={site.name}
          onDelete={displayFocused || dropdownOpen ? () => handleSiteUnselect(site.companyId, site.id) : undefined}
        />
      ))}
      {hiddenCount > 0 ? (
        <Chip
          sx={{ width: '50px' }}
          className="hidden-count"
          size="small"
          variant="outlined"
          label={`+${hiddenCount + 1}`}
        />
      ) : null}
    </Box>
  );
};
