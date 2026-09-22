import { useAppSelector } from "../../../store/hooks";
import ReportModal from "../EditReport/ReportModal";
import DeleteReportForm from "../EditReport/DeleteReportModal";
import EditReportForm from "../EditReport/EditReportForm";
import ReportSubmitButton from "../EditReport/ReportSubmitButton";
import CircularProgress from "@mui/material/CircularProgress";
export default function ReportsListModal() {
  const currentReport = useAppSelector((state) => state.report);

  const formTitle = useAppSelector((state) => state.report.formTitle);

  return (
    <>
      {/* working around multiple modals on this page, just checks on the form title state */}
      {currentReport.reportTableStatus != "loading" ? (
        formTitle == "Delete Report" ? (
          <DeleteReportForm></DeleteReportForm>
        ) : currentReport != undefined ? (
          <ReportModal
            formInfo={<EditReportForm></EditReportForm>}
            editActions={
              <ReportSubmitButton reportAction="Edit"></ReportSubmitButton>
            }
          ></ReportModal>
        ) : null
      ) : (
        <ReportModal
          formInfo={<CircularProgress size={100} />}
          editActions={<></>}
        ></ReportModal>
      )}
    </>
  );
}
