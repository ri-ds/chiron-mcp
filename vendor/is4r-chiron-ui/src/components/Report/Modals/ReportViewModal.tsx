import { Box, Typography } from "@mui/material";
import Divider from "@mui/material/Divider";

import { useAppSelector } from "../../../store/hooks";
import ShareUsersToggle from "../EditReport/ShareUsers";
import ReportModal from "../EditReport/ReportModal";
import ReportSubmitButton from "../EditReport/ReportSubmitButton";
import { Form } from "react-router-dom";

export default function ReportViewModal() {
  const reportUrl = useAppSelector((state) => state.report.fullUrl);
  const reportOwner = useAppSelector((state) => state.report.creator);
  const sharingDescription = useAppSelector(
    (state) => state.report.sharingDescription
  );

  return (
    <ReportModal
      formInfo={
        <Box>
          <Typography>
            Report Direct Link:
            {sharingDescription != "public"
              ? "(user must have the correct permissions to view)"
              : ""}
          </Typography>
          <Box
            sx={{
              bgcolor: "#f8f5f0",
              p: 1,
              m: 1,
              border: "solid 1px #dfd7ca",
            }}
          >
            <Typography>{reportUrl}</Typography>
          </Box>
          <Divider></Divider>
          {sharingDescription != "public" ? (
            <Box>
              <Form>
                <Typography sx={{ pb: 2 }}>
                  Report Owner : {reportOwner}
                </Typography>
                <Typography>Other users with access to this report:</Typography>
                <ShareUsersToggle></ShareUsersToggle>
              </Form>
            </Box>
          ) : (
            <Box>
              <Typography>
                This report is set to public and can be viewed by all users.
              </Typography>
            </Box>
          )}
        </Box>
      }
      editActions={
        <Box display={sharingDescription != "public" ? "visible" : "none"}>
          <ReportSubmitButton reportAction="Share"></ReportSubmitButton>
        </Box>
      }
    ></ReportModal>
  );
}
