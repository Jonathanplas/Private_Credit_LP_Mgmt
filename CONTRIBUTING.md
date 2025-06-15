# Contributing to LP Management System

Thank you for considering contributing to the LP Management System! This document outlines the process for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/lpmanagement.git`
3. Create a new branch for your feature: `git checkout -b feature-name`
4. Make your changes
5. Test your changes thoroughly
6. Commit your changes: `git commit -m "Description of changes"`
7. Push to your branch: `git push origin feature-name`
8. Submit a pull request

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Update the `.env` file with your database credentials
3. Set up your development environment following the instructions in the README

## Development Guidelines

### Code Style
- Follow PEP 8 style guidelines for Python code
- Use 4 spaces for indentation (no tabs)
- Keep line length to a maximum of 100 characters
- Write meaningful docstrings for functions and classes

### For Frontend Development
- Follow the existing React component patterns
- Use TypeScript interfaces for prop definitions
- Keep components focused on a single responsibility
- Write responsive and accessible code

### Testing
- Add tests for new functionality
- Ensure all tests pass before submitting a pull request
- Aim for high test coverage for critical path code

## Pull Request Process

1. Update the README.md or documentation with details of changes where appropriate
2. Update the version numbers in any example files following [SemVer](http://semver.org/)
3. The PR will be merged once it receives approvals from project maintainers

## Feature Requests and Bug Reports

Please use the GitHub issue templates to submit feature requests or bug reports.

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement

Violations of the code of conduct may be reported by contacting the project team. All complaints will be reviewed and investigated promptly and fairly. The project team is obligated to maintain confidentiality with regard to the reporter of an incident.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.
