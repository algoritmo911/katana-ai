# Contributing to this project

Thank you for your interest in contributing! We welcome all contributions, from bug fixes to new features.

# Политика ветвления

## Общие правила
1. Канонические ветки:
   - `main` — production-ready код
   - `dev` — интеграционная ветка
   - `feature/*` — активная разработка фич (каждая фича — отдельная ветка)

2. Именование веток:
   - `feature/<описание>-<issue>` (напр. `feature/supabase-memory-core-123`)
   - Не используем суффиксы `-1`, `-2`, `-copy` и т.п. — они запрещены и автоматически архивируются.

3. Рабочий процесс:
   - Перед созданием PR — выполнить `git fetch && git rebase origin/<target>` (или merge policy по договорённости).
   - PR должен иметь чёткое описание, ссылку на issue и прохождение CI.

4. Удаление веток:
   - После merge ветка удаляется на origin.
   - Если по каким-то причинам ветку нужно сохранить — переносим в `archive/<branch>`.

5. Запреты:
   - Не пушим сгенерированные артефакты в репозиторий.
   - Не создаём одноразовых дубликатов веток с `-1/-2`.

## Автоматизация (рекомендация)
- Включить GitHub Action / GitLab CI job, который:
  - помечает ветки с `-1`, `-2` и создаёт issue/PR на ревью;
  - блокирует прямое создание веток с запрещёнными суффиксами.

---

## Getting Started

1.  **Fork the repository:** Click the "Fork" button on the top right of the repository page. This will create a copy of the repository in your GitHub account.
2.  **Clone your fork:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    cd YOUR_REPOSITORY_NAME
    ```
3.  **Create a new branch:** Before making any changes, create a new branch for your work. Choose a descriptive branch name (e.g., `feature/new-widget` or `fix/login-bug`).
    ```bash
    git checkout -b your-branch-name
    ```

## Making Changes

1.  **Make your changes:** Write your code, add tests, and ensure your code follows the project's style guidelines.
2.  **Commit your changes:** Commit your changes with a clear and concise commit message.
    ```bash
    git add .
    git commit -m "feat: Add new widget for displaying user data"
    # Or for a fix:
    # git commit -m "fix: Correct issue with user login"
    ```
    Refer to [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for commit message guidelines if the project uses them.

3.  **Keep your branch up to date:** Periodically, you might want to pull in the latest changes from the main repository to avoid merge conflicts.
    ```bash
    git remote add upstream https://github.com/ORIGINAL_OWNER/ORIGINAL_REPOSITORY_NAME.git # Do this once
    git fetch upstream
    git rebase upstream/main # Or the default branch name
    ```

## Submitting Your Contribution

1.  **Push your changes:** Push your branch to your fork on GitHub.
    ```bash
    git push origin your-branch-name
    ```
2.  **Create a Pull Request (PR):** Go to the original repository on GitHub. You should see a prompt to create a pull request from your recently pushed branch. Click it, review your changes, and submit the PR.
3.  **Address feedback:** Project maintainers will review your PR and may request changes. Make the necessary updates, commit them, and push to your branch. The PR will update automatically.

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms. (If a Code of Conduct file exists, link to it here).

---

Thank you for contributing!
