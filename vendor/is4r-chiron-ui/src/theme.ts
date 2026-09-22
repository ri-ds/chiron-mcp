import { red, teal, green } from "@mui/material/colors";

// A custom theme for this app
const theme = {
  palette: {
    primary: {
      main: teal[500],
    },
    secondary: {
      main: green[600],
    },
    error: {
      main: red.A400,
    },
    text: { primary: "#565A5C" },
  },
};

export default theme;
