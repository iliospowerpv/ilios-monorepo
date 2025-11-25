import React, { Dispatch, SetStateAction } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import Zoom from '@mui/material/Zoom';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Fade from '@mui/material/Fade';

import { DetailsContainer } from './TechnicalDetail.styles';
import Inverter from './devices/Inverter/Inverter';
import Module from './devices/Module/Module';
import Modem from './devices/Modem/Modem';
import RackMount from './devices/RackMount/RackMount';
import Camera from './devices/Camera/Camera';
import Meter from './devices/Meter/Meter';
import Transformer from './devices/Transformer/Transformer';
import NetworkConnection from './devices/NetworkConnection/NetworkConnection';
import Battery from './devices/Battery/Battery';
import CombinerBox from './devices/CombinerBox/CombinerBox';
import MBODGateway from './devices/MBODGateway/MBODGateway';
import NetworkGateway from './devices/NetworkGateway/NetworkGateway';
import WeatherStation from './devices/WeatherStation/WeatherStation';

type CategoryType =
  | 'Inverter'
  | 'Module'
  | 'Meter'
  | 'Rack Mount'
  | 'Battery'
  | 'Camera'
  | 'Combiner Box'
  | 'Modem'
  | 'MBOD Gateway'
  | 'Weather Station'
  | 'Network Connection'
  | 'Network Gateway'
  | 'Transformer';

interface TechnicalDetailsProps {
  technicalDetailData: any;
  deviceCategory: CategoryType;
  siteId: number;
  deviceId: number;
}

export interface DeviceTechnicalDetailsFormReflectedState {
  isValid: boolean;
  isDirty: boolean;
  isSubmitting: boolean;
}

export interface DeviceTechnicalDetailsFormProps {
  mode: 'view' | 'edit';
  category: CategoryType;
  siteId: number;
  deviceId: number;
  technicalDetailsData: any;
  reflectFormState: (state: DeviceTechnicalDetailsFormReflectedState) => void;
  setMode: Dispatch<SetStateAction<'view' | 'edit'>>;
}

export interface DeviceTechnicalDetailsFormRef {
  resetForm: () => void;
  submit: () => void;
}

interface DeviceData {
  category: string;
  content: React.ForwardRefExoticComponent<
    DeviceTechnicalDetailsFormProps & React.RefAttributes<DeviceTechnicalDetailsFormRef>
  > | null;
}

const devicesData: DeviceData[] = [
  {
    category: 'Inverter',
    content: Inverter
  },
  {
    category: 'Module',
    content: Module
  },
  {
    category: 'Meter',
    content: Meter
  },
  {
    category: 'Rack Mount',
    content: RackMount
  },
  {
    category: 'Battery',
    content: Battery
  },
  {
    category: 'Camera',
    content: Camera
  },
  {
    category: 'Combiner Box',
    content: CombinerBox
  },
  {
    category: 'Modem',
    content: Modem
  },
  {
    category: 'MBOD Gateway',
    content: MBODGateway
  },
  {
    category: 'Weather Station',
    content: WeatherStation
  },
  {
    category: 'Network Connection',
    content: NetworkConnection
  },
  {
    category: 'Network Gateway',
    content: NetworkGateway
  },
  {
    category: 'Transformer',
    content: Transformer
  }
];

export const TechnicalDetailCard: React.FC<TechnicalDetailsProps> = ({
  siteId,
  deviceId,
  deviceCategory,
  technicalDetailData
}) => {
  const [mode, setMode] = React.useState<'view' | 'edit'>('view');
  const [formReflectedState, setFormReflectedState] = React.useState<DeviceTechnicalDetailsFormReflectedState>({
    isValid: false,
    isDirty: false,
    isSubmitting: false
  });
  const formApi = React.useRef<DeviceTechnicalDetailsFormRef | null>(null);

  const { isValid, isDirty, isSubmitting } = formReflectedState;

  const DisplayContent = React.useMemo(() => {
    const device = devicesData.find(({ category }) => category === deviceCategory);
    return device ? device.content : null;
  }, [deviceCategory]);

  const handleClickEdit = () => setMode('edit');

  const handleClickCancel = () => {
    formApi.current && formApi.current.resetForm();
    setMode('view');
  };

  const handleClickSave = () => {
    formApi.current && formApi.current.submit();
  };

  return (
    <Box>
      <DetailsContainer position="relative" display="flex" flexDirection="column" flexGrow={1}>
        <Stack direction="row" p="8px" pb="16px" flexWrap="nowrap" justifyContent="space-between" alignItems="center">
          <Typography variant="h5" mb="0">
            Technical Details
          </Typography>
          <Zoom in={mode === 'view'}>
            <Box borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
              <IconButton
                data-testid="service_details-general_device_info-edit_btn"
                size="small"
                onClick={handleClickEdit}
              >
                <EditIcon fontSize="small" sx={{ color: '#404251' }} />
              </IconButton>
            </Box>
          </Zoom>
        </Stack>
        <Box px="8px">
          <Divider sx={{ borderBottom: '1px solid #0000003B', height: '1px', marginBottom: '8px' }} />
        </Box>
        {DisplayContent && (
          <DisplayContent
            ref={formApi}
            mode={mode}
            category={deviceCategory}
            siteId={siteId}
            deviceId={deviceId}
            setMode={setMode}
            technicalDetailsData={technicalDetailData}
            reflectFormState={setFormReflectedState}
          />
        )}
        <Stack
          width="100%"
          direction="row"
          flexWrap="nowrap"
          alignItems="center"
          justifyContent="flex-end"
          px="8px"
          pt="16px"
          pb="8px"
        >
          {mode === 'edit' && (
            <Fade in={mode === 'edit'} timeout={{ enter: 1000, exit: 1000 }}>
              <Stack direction="row" spacing={1}>
                <Button
                  disabled={!isValid || !isDirty || isSubmitting}
                  variant="contained"
                  size="small"
                  onClick={handleClickSave}
                >
                  Save
                </Button>
                <Button disabled={isSubmitting} variant="outlined" size="small" onClick={handleClickCancel}>
                  Cancel
                </Button>
              </Stack>
            </Fade>
          )}
        </Stack>
      </DetailsContainer>
    </Box>
  );
};

export default TechnicalDetailCard;
