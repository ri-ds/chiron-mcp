import { useAppSelector } from "../../../store/hooks";
import ReportModal from "./ReportModal";
import ReportSubmitButton from "./ReportSubmitButton";

export default function DeleteReportForm() {
  const currentReport = useAppSelector((state) => state.report);

  return (
    <ReportModal
      formInfo={
        <p>
          Are you sure you want to permanently delete the report "
          {currentReport.name}"? This action can't be undone.
        </p>
      }
      editActions={
        <ReportSubmitButton reportAction="Delete"></ReportSubmitButton>
      }
    ></ReportModal>
  );
}
