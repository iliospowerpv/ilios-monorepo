import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import { ApiClient, DeviceDetailedInfo } from '../../../../../../../api';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';
import { ConfirmationModal } from '../../../../../../../components/modals/ConfirmationModal/ConfirmationModal';

interface DeviceActionsPanelProps {
  siteId: number;
  deviceId: number;
  companyId: number;
  deviceDetails: DeviceDetailedInfo;
}

type UpdateDeviceGeneralInfo = typeof ApiClient.assetManagement.updateDeviceGeneralInfo;
type UpdateDeviceGeneralInfoAttributes = Parameters<UpdateDeviceGeneralInfo>[number]['attributes'];

export const DeviceActionsPanel: React.FC<DeviceActionsPanelProps> = ({ siteId, deviceId, deviceDetails }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();

  const [confirmationModalOpen, setConfirmationModalOpen] = React.useState(false);

  const { mutateAsync: updateDevice, isPending: isUpdateDevicePending } = useMutation({
    mutationFn: (attributes: UpdateDeviceGeneralInfoAttributes) =>
      ApiClient.assetManagement.updateDeviceGeneralInfo({ siteId, deviceId, attributes })
  });

  const handleClickDecommission = (): void => {
    setConfirmationModalOpen(true);
  };
  const handleModalClose = (): void => {
    setConfirmationModalOpen(false);
  };
  const handleModalConfirm = async (): Promise<void> => {
    try {
      const response = await updateDevice({
        status: 'Decommissioned',
        asset_id: deviceDetails.general_info.asset_id,
        name: deviceDetails.general_info.name,
        type: deviceDetails.general_info.type === 'Other' ? null : deviceDetails.general_info.type,
        manufacturer:
          deviceDetails.general_info.manufacturer === 'Other'
            ? deviceDetails.general_info.category === 'Network Connection'
              ? deviceDetails.general_info.manufacturer
              : null
            : deviceDetails.general_info.manufacturer,
        model: deviceDetails.general_info.model,
        serial_number: deviceDetails.general_info.serial_number,
        warranty_effective_date: deviceDetails.general_info.warranty_effective_date,
        warranty_term: deviceDetails.general_info.warranty_term,
        gateway_id: deviceDetails.general_info.gateway_id,
        function_id: deviceDetails.general_info.function_id,
        driver: deviceDetails.general_info.driver,
        install_date: deviceDetails.general_info.install_date,
        decommissioned_date: deviceDetails.general_info.decommissioned_date,
        last_updated_date: deviceDetails.general_info.last_updated_date
      });
      queryClient.invalidateQueries({ queryKey: ['device'] });
      notify(response.message || `Device was successfully updated.`);
      setConfirmationModalOpen(false);
    } catch (e: any) {
      notify(e?.response?.data?.message || 'Device update failed');
    }
  };

  const deviceStatus = deviceDetails.general_info.status;

  return (
    <>
      <Stack
        sx={{
          marginTop: '-8px',
          marginBottom: '6px',
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '16px'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Button variant="contained" color="primary">
            Reset
          </Button>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Button
            variant="contained"
            color="primary"
            disabled={deviceStatus === 'Decommissioned'}
            onClick={handleClickDecommission}
          >
            Decommission
          </Button>
        </Box>
      </Stack>
      <ConfirmationModal
        open={confirmationModalOpen}
        confirmationMessage="Are you sure you want to change the status of this device to 'Decommissioned'?"
        confirmationDisabled={isUpdateDevicePending}
        onClose={handleModalClose}
        onConfirm={handleModalConfirm}
      />
    </>
  );
};
