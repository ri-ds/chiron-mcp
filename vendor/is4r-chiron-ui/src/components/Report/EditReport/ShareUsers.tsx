import { FormGroup } from "@mui/material";

import { updateShareUsers } from "../../../store/reportSlice";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import Select from "react-select";

export default function ShareUsersToggle() {
  const dispatch = useAppDispatch();
  const sharedUsers = useAppSelector((state) => state.report.sharedUsers);
  if (sharedUsers.length < 1) {
    return null;
  }

  return (
    <FormGroup>
      <Select
        menuPortalTarget={document.body}
        styles={{ menuPortal: (base) => ({ ...base, zIndex: 9999 }) }}
        defaultValue={sharedUsers.filter((user) => user.checked)}
        isMulti
        menuPosition="fixed"
        getOptionLabel={(data) => data?.username}
        getOptionValue={(data) => data?.user_id.toString()}
        options={sharedUsers}
        onChange={(values) => {
          dispatch(updateShareUsers(values));
        }}
      />
    </FormGroup>
  );
}
