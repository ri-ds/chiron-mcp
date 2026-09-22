import { Button } from "@mui/material";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import {
  editReport,
  createReport,
  deleteReport,
  shareReport,
  toggleShareDialog,
  toggleReportSaveSuccessDialog,
} from "../../../store/reportSlice";
import { ReportFormData } from "../../../store/reportSlice";
import { loadReportCategories } from "../../../store/reportsSlice";

export default function ReportSubmitButton(props: {
  reportAction: "Create" | "Edit" | "Delete" | "Share" | "Overwrite";
}) {
  const dispatch = useAppDispatch();
  const currentReport = useAppSelector((state) => state.report);
  const currentDataset = useAppSelector((state) => state.auth.dataset);

  const actionData: {
    reportId?: number | undefined;
    postData: ReportFormData | undefined;
  } = {
    reportId: currentReport.selectedReport,
    postData: {
      newName: currentReport.name,
      overwrite_query_def_with_active: "no",
      project: currentReport.projectId != -1 ? currentReport.projectId : "",
      project_other: currentReport.projectId == -1 ? currentReport.project : "",
      description: currentReport.description,
      publicBool: currentReport.public,
      share_with: currentReport.sharedUsers,
      dataset: currentDataset?.id,
    },
  };

  type FuncAction = {
    data: {
      reportId?: number | undefined;
      postData?: ReportFormData | undefined;
    };
    display: string;
  };

  const funcActionDict: {
    Create: FuncAction;
    Edit: FuncAction;
    Delete: FuncAction;
    Share: FuncAction;
    Overwrite: FuncAction;
  } = {
    Create: {
      data: { ...actionData },
      display: "Save",
    },
    Edit: {
      data: { ...actionData },
      display: "Edit",
    },
    Delete: {
      data: { ...actionData },
      display: "Yes, Delete Report",
    },
    Share: {
      data: { ...actionData },
      display: "Save",
    },
    Overwrite: {
      data: {
        reportId: actionData.reportId,
        postData: {
          ...actionData.postData,
          overwrite_query_def_with_active: "yes",
        },
      },
      display: "Overwrite",
    },
  };
  const submitButtonInfo = funcActionDict[props.reportAction];
  return (
    <Button
      type="submit"
      variant="contained"
      disabled={
        (currentReport.selectedReport == -1 &&
          props.reportAction == "Overwrite") ||
        currentReport.errors.length > 0 ||
        currentReport.project == "--- create new ---" ||
        currentReport.project?.trim() == "" ||
        (props.reportAction == "Create" &&
          currentReport.name?.trim() != "" &&
          currentReport.name == "---select a report---")
      }
      color={props.reportAction == "Delete" ? "error" : "primary"}
      onClick={function () {
        const pData = submitButtonInfo.data;

        switch (props.reportAction) {
          case "Create":
            dispatch(
              createReport({
                dataset: currentDataset ? currentDataset.unique_id : "",
                reportId: pData.reportId,
                postData: pData.postData,
              })
            );
            dispatch(
              loadReportCategories({
                dataset: currentDataset?.unique_id
                  ? currentDataset.unique_id
                  : "",
              })
            );
            break;
          case "Edit":
            dispatch(
              editReport({
                dataset: currentDataset ? currentDataset.unique_id : "",
                reportId: pData.reportId,
                postData: pData.postData,
              })
            );
            dispatch(
              loadReportCategories({
                dataset: currentDataset?.unique_id
                  ? currentDataset.unique_id
                  : "",
              })
            );
            break;
          case "Delete":
            dispatch(
              deleteReport({
                dataset: currentDataset ? currentDataset.unique_id : "",
                reportId: pData.reportId,
                postData: pData.postData,
              })
            );
            dispatch(
              loadReportCategories({
                dataset: currentDataset?.unique_id
                  ? currentDataset.unique_id
                  : "",
              })
            );
            break;
          case "Share":
            dispatch(
              shareReport({
                dataset: currentDataset ? currentDataset.unique_id : "",
                reportId: pData.reportId,
                postData: pData.postData,
              })
            );
            // dispatch(loadReportTableDef())
            break;
          case "Overwrite":
            dispatch(
              editReport({
                dataset: currentDataset ? currentDataset.unique_id : "",
                reportId: pData.reportId,
                postData: pData.postData,
              })
            );
            dispatch(
              loadReportCategories({
                dataset: currentDataset?.unique_id
                  ? currentDataset.unique_id
                  : "",
              })
            );
            break;
        }

        dispatch(toggleShareDialog());
        if (
          props.reportAction == "Create" ||
          props.reportAction == "Overwrite"
        ) {
          dispatch(toggleReportSaveSuccessDialog());
        }
      }}
    >
      {submitButtonInfo.display}
    </Button>
  );
}
