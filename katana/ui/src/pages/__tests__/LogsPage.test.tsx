import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LogsPage from '../LogsPage'; // Adjust path if LogsPage is elsewhere

// Mock the child components
// The path should be relative to *this test file's location* or use aliases if Jest config handles them.
// Assuming LogViewer and LogConfiguration are in ../../components/ from src/pages/__tests__/
jest.mock('../../components/LogViewer', () => () => <div data-testid="log-viewer-mock">LogViewer Mock Content</div>);
jest.mock('../../components/LogConfiguration', () => () => <div data-testid="log-configuration-mock">LogConfiguration Mock Content</div>);

describe('LogsPage Component', () => {
  test('renders the main heading and section headings', () => {
    render(<LogsPage />);

    // Check for the main page heading
    expect(screen.getByRole('heading', { level: 1, name: /application logs & configuration/i })).toBeInTheDocument();

    // Check for section headings
    expect(screen.getByRole('heading', { level: 2, name: /log configuration/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /log viewer/i })).toBeInTheDocument();
  });

  test('renders mocked LogConfiguration and LogViewer components', () => {
    render(<LogsPage />);

    // Check if the mocked child components are rendered by checking their mock content and test IDs
    const logConfigMock = screen.getByTestId('log-configuration-mock');
    expect(logConfigMock).toBeInTheDocument();
    expect(logConfigMock).toHaveTextContent('LogConfiguration Mock Content');

    const logViewerMock = screen.getByTestId('log-viewer-mock');
    expect(logViewerMock).toBeInTheDocument();
    expect(logViewerMock).toHaveTextContent('LogViewer Mock Content');
  });

  test('has the main page div with correct class and contains sections', () => {
    const { container } = render(<LogsPage />);

    // Check for the main div with class "logs-page"
    // Note: React Testing Library encourages querying by roles/text accessible to users.
    // Checking classes is more of an implementation detail test.
    const firstChild = container.firstChild;
    expect(firstChild).toHaveClass('logs-page');

    // Check if there are two <section> elements within the first child
    if (firstChild) {
      const sections = (firstChild as HTMLElement).querySelectorAll('section');
      expect(sections.length).toBe(2);
    } else {
      throw new Error("Container first child not found, cannot check for sections.");
    }
  });
});
