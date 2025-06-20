module.exports = {
  preset: 'ts-jest', // Use ts-jest for TypeScript files
  testEnvironment: 'jsdom', // Simulate a browser environment
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'], // Setup file for extending jest matchers
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy', // Mock CSS imports
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@pages/(.*)$': '<rootDir>/src/pages/$1',
    // Ensure this matches how your actual UI code might import from parent 'katana' if ever needed,
    // though typically UI components wouldn't reach outside 'katana/ui/src' like that.
    // For imports within the UI project itself, the above aliases for @components and @pages are typical.
  },
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: 'tsconfig.json',
      // diagnostics: {
      //   ignoreCodes: ['TS151001'], // Example: If you need to ignore specific TS diagnostic codes during test compilation
      // },
    }],
    '^.+\\.(js|jsx)$': ['babel-jest', { presets: ['@babel/preset-env', '@babel/preset-react', '@babel/preset-typescript'] }],
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  // globals: { // 'ts-jest' globals are usually set within the transform options as above
  //   'ts-jest': {
  //     tsconfig: 'tsconfig.json',
  //   },
  // },
  // Automatically clear mock calls and instances between every test
  clearMocks: true,
  // The directory where Jest should output its coverage files
  coverageDirectory: "coverage",
  // Indicates whether the coverage information should be collected while executing the test
  collectCoverage: true,
  collectCoverageFrom: [ // Specify files to include in coverage report
    "src/**/*.{ts,tsx}",
    "!src/**/*.d.ts", // Exclude type definition files
    "!src/main.tsx", // Exclude main entry point if it's just rendering App
    "!src/vite-env.d.ts", // Exclude vite env types
    "!src/setupTests.ts", // Exclude test setup files
  ],
};
