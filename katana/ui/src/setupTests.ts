// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// You can add other global setup here if needed.
// For example, mocking global objects or functions:
/*
jest.mock('./some-module', () => ({
  ...jest.requireActual('./some-module'), // Import and retain default behavior
  specificFunction: jest.fn().mockReturnValue('mocked value'), // Mock specific function
}));

// Mocking fetch globally for all tests if needed
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ data: 'mocked data' }),
    ok: true,
    status: 200,
  } as Response)
);
*/

// Clean up after tests if necessary, e.g., by clearing mocks
// This is often handled by Jest's own config (clearMocks: true) but can be extended.
// afterEach(() => {
//   jest.clearAllMocks();
// });
