# Contributing to Image to 3D Environment Generator

Thank you for your interest in contributing! This project is completely free and open-source, and we welcome contributions from everyone.

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/image-to-3d-generator/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your environment (OS, Python version, browser)

### Suggesting Features

1. Check [Issues](https://github.com/yourusername/image-to-3d-generator/issues) for similar suggestions
2. Open a new issue with the "Feature Request" label
3. Describe:
   - The problem it solves
   - Proposed solution
   - Alternative solutions considered
   - Whether you'd like to implement it

### Contributing Code

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/image-to-3d-generator.git
   cd image-to-3d-generator
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   ```bash
   cd backend
   pytest
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "Add feature: brief description"
   ```

6. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Code Style

### Python (Backend)
- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and modular

### JavaScript (Frontend)
- Use modern ES6+ syntax
- Add JSDoc comments for complex functions
- Follow existing formatting
- Use descriptive variable names

### General
- Keep lines under 100 characters when possible
- Use clear, descriptive commit messages
- Add comments for non-obvious code
- Update README if adding new features

## 🎯 Good First Issues

Look for issues labeled `good first issue` - these are perfect for newcomers!

Ideas for contributions:
- Improve error messages
- Add more example images
- Enhance documentation
- Optimize performance
- Add new procedural generation rules
- Improve mobile responsiveness
- Add unit tests

## 🧪 Testing

Before submitting a PR:
1. Test the backend API endpoints
2. Test the frontend UI flow
3. Test with various image types and sizes
4. Verify exports work in Unity/Unreal/Blender
5. Check for memory leaks with large images

## 📚 Documentation

Good documentation is just as important as code:
- Update README.md for new features
- Add inline code comments
- Update API documentation
- Create examples for new functionality

## 🔍 Review Process

1. Automated checks will run on your PR
2. Maintainers will review your code
3. Address any requested changes
4. Once approved, your PR will be merged!

## 💡 Ideas for Major Contributions

- Support for additional AI models (Depth Anything, etc.)
- GPU acceleration
- Real-time preview during generation
- Advanced mesh optimization
- Texture synthesis for unseen areas
- Batch processing
- Unity/Unreal plugins
- Mobile app

## ❓ Questions?

Feel free to:
- Open a discussion in [GitHub Discussions](https://github.com/yourusername/image-to-3d-generator/discussions)
- Comment on relevant issues
- Reach out to maintainers

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Remember: we're all here to learn and build something cool!

## 🙏 Thank You!

Every contribution, no matter how small, makes this project better for everyone. Thank you for being part of the open-source community!
