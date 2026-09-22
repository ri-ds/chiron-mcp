import { blue } from "@mui/material/colors";
import { styled } from "@mui/material/styles";
import Tooltip, { TooltipProps, tooltipClasses } from "@mui/material/Tooltip";

const LightTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  [`& .${tooltipClasses.tooltip}`]: {
    backgroundColor: theme.palette.common.white,
    color: "rgba(0, 0, 0, 0.87)",
    boxShadow: theme.shadows[1],
    border: "1px solid",
    borderColor: blue[200],
    p: 1,
    fontSize: 12,
  },
  ".MuiTooltip-arrow": {
    color: theme.palette.common.white,
  },
}));

export default LightTooltip;
