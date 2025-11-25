import React from 'react';
import { useControls } from 'react-zoom-pan-pinch';
import { styled } from '@mui/material/styles';

const Container = styled('div')(({ theme }) => ({
  display: 'flex',
  position: 'absolute',
  top: 0,
  left: 0,
  zIndex: 1,
  width: '100%',
  height: '56px',
  justifyContent: 'flex-start',
  alignItems: 'center',
  padding: '8px 20px',
  backgroundColor: '#fff',
  boxShadow: 'none',
  borderBottom: '1px solid #E0E0E0',
  background: theme.palette.common.white,
  '@media (max-width: 768px)': {
    padding: '6px'
  },
  '& > *': {
    color: theme.palette.text.secondary,
    boxShadow: 'none',
    margin: '0px 8px'
  },
  path: {
    fill: theme.palette.text.secondary
  },
  polygon: {
    fill: theme.palette.text.secondary
  }
}));

const ControlButton = styled('button')`
  color: #4f4f4f;
  box-shadow: none;
  margin: 0px 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  text-align: center;
  font-size: 18px;
  border: 0;
  outline: none;
  cursor: pointer;
  text-decoration: none;
  border-radius: 35px;
  opacity: 1;
  pointer-events: all;
  background: ${({ theme }) => theme.palette.common.white};
  @media (max-width: 768px) {
    width: 25px;
    height: 25px;
    font-size: 15px;
  }
`;

interface IconProps {
  color?: string;
  size?: string | number | string | undefined;
  reverse?: boolean;
}

export const ZoomInImageIcon = (props: IconProps) => {
  return <ZoomImageIcon {...props} />;
};

export const ZoomOutImageIcon = (props: IconProps) => {
  return <ZoomImageIcon {...props} reverse />;
};

const ZoomImageIcon = (props: IconProps) => {
  const { color, size, reverse } = props;
  return (
    <svg width={size || '100%'} height={size || '100%'} viewBox="0 0 32 32" version="1.1">
      <g id="page" stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
        <g id="search-plus-icon" fill={color || '#aaa'}>
          <path
            id="search-plus"
            d={
              reverse
                ? 'M 13 13 L 16 13 L 19 13 L 19 16 L 16 16 L 13 16 L 10 16 L 10 13 Z M 19.4271 21.4271 C 18.0372 22.4175 16.3367 23 14.5 23 C 9.8056 23 6 19.1944 6 14.5 C 6 9.8056 9.8056 6 14.5 6 C 19.1944 6 23 9.8056 23 14.5 C 23 16.3367 22.4175 18.0372 21.4271 19.4271 L 27.0119 25.0119 C 27.5621 25.5621 27.5575 26.4425 27.0117 26.9883 L 26.9883 27.0117 C 26.4439 27.5561 25.5576 27.5576 25.0119 27.0119 L 19.4271 21.4271 L 19.4271 21.4271 L 19.4271 21.4271 Z M 14.5 21 C 18.0899 21 21 18.0899 21 14.5 C 21 10.9101 18.0899 8 14.5 8 C 10.9101 8 8 10.9101 8 14.5 C 8 18.0899 10.9101 21 14.5 21 L 14.5 21 Z'
                : 'M 13 13 L 13 10 L 16 10 L 16 13 L 19 13 L 19 16 L 16 16 L 16 19 L 13 19 L 13 16 L 10 16 L 10 13 Z M 19.4271 21.4271 C 18.0372 22.4175 16.3367 23 14.5 23 C 9.8056 23 6 19.1944 6 14.5 C 6 9.8056 9.8056 6 14.5 6 C 19.1944 6 23 9.8056 23 14.5 C 23 16.3367 22.4175 18.0372 21.4271 19.4271 L 27.0119 25.0119 C 27.5621 25.5621 27.5575 26.4425 27.0117 26.9883 L 26.9883 27.0117 C 26.4439 27.5561 25.5576 27.5576 25.0119 27.0119 L 19.4271 21.4271 L 19.4271 21.4271 L 19.4271 21.4271 Z M 14.5 21 C 18.0899 21 21 18.0899 21 14.5 C 21 10.9101 18.0899 8 14.5 8 C 10.9101 8 8 10.9101 8 14.5 C 8 18.0899 10.9101 21 14.5 21 L 14.5 21 Z'
            }
          />
        </g>
      </g>
    </svg>
  );
};

export const ResetZoomImageIcon = (props: IconProps) => {
  const { color, size } = props;
  return (
    <svg width={size || '100%'} height={size || '100%'} viewBox="0 0 24 24">
      <path
        fill={color || '#aaa'}
        d="M9.29,13.29,4,18.59V17a1,1,0,0,0-2,0v4a1,1,0,0,0,.08.38,1,1,0,0,0,.54.54A1,1,0,0,0,3,22H7a1,1,0,0,0,0-2H5.41l5.3-5.29a1,1,0,0,0-1.42-1.42ZM5.41,4H7A1,1,0,0,0,7,2H3a1,1,0,0,0-.38.08,1,1,0,0,0-.54.54A1,1,0,0,0,2,3V7A1,1,0,0,0,4,7V5.41l5.29,5.3a1,1,0,0,0,1.42,0,1,1,0,0,0,0-1.42ZM21,16a1,1,0,0,0-1,1v1.59l-5.29-5.3a1,1,0,0,0-1.42,1.42L18.59,20H17a1,1,0,0,0,0,2h4a1,1,0,0,0,.38-.08,1,1,0,0,0,.54-.54A1,1,0,0,0,22,21V17A1,1,0,0,0,21,16Zm.92-13.38a1,1,0,0,0-.54-.54A1,1,0,0,0,21,2H17a1,1,0,0,0,0,2h1.59l-5.3,5.29a1,1,0,0,0,0,1.42,1,1,0,0,0,1.42,0L20,5.41V7a1,1,0,0,0,2,0V3A1,1,0,0,0,21.92,2.62Z"
      />
    </svg>
  );
};

export const DocImageRendererZoomControls: React.FC = () => {
  const { zoomIn, zoomOut, resetTransform } = useControls();

  return (
    <Container id="image-zoom-controls">
      <ControlButton id="image-zoom-out" data-testid="image-preview-controls-zoom-out" onMouseDown={() => zoomOut()}>
        <ZoomOutImageIcon color="#000" size="80%" />
      </ControlButton>

      <ControlButton id="image-zoom-in" data-testid="image-preview-controls-zoom-in" onMouseDown={() => zoomIn()}>
        <ZoomInImageIcon color="#000" size="80%" />
      </ControlButton>

      <ControlButton
        id="image-zoom-reset"
        data-testid="image-preview-controls-zoom-reset"
        onMouseDown={() => resetTransform()}
      >
        <ResetZoomImageIcon color="#000" size="70%" />
      </ControlButton>
    </Container>
  );
};
