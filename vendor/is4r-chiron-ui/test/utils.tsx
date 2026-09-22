/* eslint-disable react-refresh/only-export-components */
import type { RenderOptions } from "@testing-library/react";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { InitialEntry } from "history";
import * as React from "react";
import { ThemeProvider } from "@emotion/react";
import { CssBaseline } from "@mui/material";
import theme from "../src/theme";
import {
  RouterProvider,
  MemoryRouter,
  createBrowserRouter,
} from "react-router-dom";
import type { BrowserRouter } from "react-router-dom";
import routeConfig from "../src/routeConfig";
import router from "../src/router";
import { Provider } from "react-redux";
import { setupStore } from "../src/store";
import type { AppStore, RootState } from "../src/store";
import type { PreloadedState } from "@reduxjs/toolkit";

export interface ProviderOptions extends RenderOptions {
  initialEntries?: Array<InitialEntry>;
  preloadedState?: object;
  route?: string;
}

export interface ProvidersProps extends ProviderOptions {
  children: React.ReactNode;
  routerObj?: typeof BrowserRouter;
  preloadedState?: PreloadedState<RootState>;
  store?: AppStore;
}

function Providers({ routerObj, preloadedState, store }: ProvidersProps) {
  if (!store) {
    store = setupStore(preloadedState);
  }
  if (!routerObj) {
    routerObj = router;
  }
  return (
    <React.Suspense fallback={null}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Provider store={setupStore(preloadedState)}>
          <RouterProvider router={routerObj} />
        </Provider>
      </ThemeProvider>
    </React.Suspense>
  );
}

function renderWithProviders(
  ui: React.ReactElement,
  options: ProviderOptions = {}
) {
  const { initialEntries = [], preloadedState, ...rest } = options;
  for (const i in initialEntries) {
    window.history.pushState({}, "", initialEntries[i].toString());
  }
  const routerObj = createBrowserRouter(routeConfig, { window: window });
  const rtl = render(ui, {
    wrapper: ({ children }) => (
      <Providers routerObj={routerObj} preloadedState={preloadedState}>
        {children}
      </Providers>
    ),
    ...rest,
  });

  return {
    ...rtl,
    rerender: (ui: React.ReactElement, rerenderOptions?: ProviderOptions) =>
      renderWithProviders(ui, {
        container: rtl.container,
        ...options,
        ...rerenderOptions,
      }),
    history,
  };
}

// This type interface extends the default options for render from RTL, as well
// as allows the user to specify other things such as initialState, store.
interface ExtendedRenderOptions extends Omit<RenderOptions, "queries"> {
  preloadedState?: PreloadedState<RootState>;
  store?: AppStore;
}

function renderComponent(
  ui: React.ReactElement,
  {
    preloadedState = { auth: { authStatus: "idle" } },
    // Automatically create a store instance if no store was passed in
    store = setupStore(preloadedState),
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: React.PropsWithChildren<object>): JSX.Element {
    return (
      <MemoryRouter initialEntries={["/"]}>
        <Provider store={store}>{children}</Provider>
      </MemoryRouter>
    );
  }

  // Return an object with the store and all of RTL's query functions
  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}

export { screen } from "@testing-library/react";

export {
  render as defaultRender,
  renderWithProviders as render,
  renderComponent,
  userEvent as user,
};
