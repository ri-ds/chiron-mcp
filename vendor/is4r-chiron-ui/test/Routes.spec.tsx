import { describe, test, expect, vi } from "vitest";
import { screen, render } from "./utils";
//import userEvent from '@testing-library/user-event';
//import { MemoryRouter } from 'react-router-dom'
import { AUTHENTICATED_USER_AUTH_STATE } from "./mocks";
import App from "../src/App";
//import initialState from "../src/store/cohortSlice"

describe("Page routing tests", () => {
  //   test("Can navigate to reports page", async () => {
  //     const authState = {
  //       preloadedState: {
  //         auth: AUTHENTICATED_USER_AUTH_STATE,
  //       },
  //     };
  //     render(<App></App>, authState);
  //     expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
  //       /route/i
  //     );
  //     await userEvent.click(screen.getByText(/reports/i));
  //     expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
  //       /route/i
  //     );
  //   });
  //   test("Can navigate to results page", async () => {
  //     const authState = {
  //       preloadedState: {
  //         auth: AUTHENTICATED_USER_AUTH_STATE,
  //       },
  //     };
  //     render(<App></App>, authState);
  //     expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
  //       /route/i
  //     );
  //     await userEvent.click(screen.getByText(/results/i));
  //     expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
  //       /route/i
  //     );
  //   });
  //   test("Can navigate to home page", async () => {
  //     const authState = {
  //       preloadedState: {
  //         auth: AUTHENTICATED_USER_AUTH_STATE,
  //       },
  //     };
  //     render(<App></App>, authState);
  //     expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
  //       /route/i
  //     );
  //     await userEvent.click(screen.getByText("Home"));
  //     expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
  //       /route/i
  //     );
  //   });
  //   // Still can't get this one working
  //   //   test('Can navigate to query page', async () => {
  //   //       const cohortState = {
  //   //           ...initialState,
  //   //           queryConcept: undefined,
  //   //           queryConceptData: undefined
  //   //       }
  //   //       render(
  //   //           <App></App>, {
  //   //           preloadedState: {
  //   //               auth: AUTHENTICATED_USER_AUTH_STATE,
  //   //               cohort: cohortState
  //   //           }
  //   //       })
  //   //       expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent(/home route/i)
  //   //       await userEvent.click(screen.getByText("Query"))
  //   //       expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent(/welcome/i)
  //   //   })
  test("Bad URL navigates to error page", async function () {
    vi.spyOn(console, "error").mockImplementation(() => null);
    render(<App></App>, {
      initialEntries: ["/bad_url"],
      preloadedState: {
        auth: AUTHENTICATED_USER_AUTH_STATE,
      },
    });
    expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent(
      "Unexpected Error"
    );
  });
});
