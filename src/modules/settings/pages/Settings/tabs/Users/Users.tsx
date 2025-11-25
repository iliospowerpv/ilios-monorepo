import React, { useEffect, useState } from 'react';

import UsersTable from '../../../../../../components/common/tables/UsersTable/UsersTable';
import EditTable from '../../../../../../components/common/tables/EditTable/EditTable';
import ToggleGroup from '../../components/ToogleGroup/ToggleGroup';
import { Role } from '../../../../../../api';
import { useRolesSettings } from '../../../../../../hooks/settings/roles';

const Users = () => {
  const [rolesRowData, setRolesRowData] = useState<Role[]>([]);
  const { data, isLoading } = useRolesSettings();
  const [alignment, setAlignment] = React.useState('list');

  useEffect(() => {
    if (!isLoading && data) {
      setRolesRowData(data);
    }
  }, [data, isLoading]);

  return (
    <>
      {alignment === 'list' && (
        <UsersTable
          searchPlaceholder="Search by Name or Email"
          btnAddLabel="Add a New User"
          customActions={<ToggleGroup alignment={alignment} setAlignment={setAlignment} />}
        />
      )}
      {alignment === 'roles' && (
        <EditTable
          rowData={rolesRowData}
          customActions={<ToggleGroup alignment={alignment} setAlignment={setAlignment} />}
        />
      )}
    </>
  );
};

export default Users;
