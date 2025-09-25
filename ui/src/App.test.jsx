import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App.tsx';

test('renders dashboard title', () => {
  render(<App />);
  const linkElement = screen.getByText(/Katana Dashboard/i);
  expect(linkElement).toBeInTheDocument();
});