import { Box } from "@mui/material";
import { darken } from "@mui/material/styles";
import config from "../config";
import { useAppSelector } from "../store/hooks";

export default function Footer() {
  const chironVersion = useAppSelector((state) => state.auth.chironVersion);
  const siteTitle = useAppSelector((state) => state.auth?.dataset?.siteTitle);

  return (
    <Box
      display="flex"
      justifyContent="space-evenly"
      alignItems="center"
      position="fixed"
      bottom={0}
      width="100%"
      p={2}
      color={config.footer.textColor}
      bgcolor={config.footer.backgroundColor}
      borderTop="1px solid"
      borderColor={darken(config.footer.backgroundColor, 0.1)}
    >
      {config.footer.leftContent ? (
        <div>{config.footer.leftContent}</div>
      ) : null}
      {config.footer.middleContent ?? (
        <Box textAlign="center" display="flex">
          <Box mr={1}>&copy; {new Date().getFullYear()}</Box>
          <Box>
            {siteTitle ?? "Chiron"} {chironVersion}
          </Box>
        </Box>
      )}
      {config.footer.leftContent ? (
        <div>{config.footer.rightContent}</div>
      ) : null}
    </Box>
  );
}
