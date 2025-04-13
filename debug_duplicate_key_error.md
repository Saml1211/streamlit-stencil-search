# Debugging Duplicate Key Error: `close_preview`

## Error Encountered

While using the Streamlit UI, specifically when interacting with the shape preview feature (likely triggered from the Stencil Health page), the following error occurred:

```
streamlit.errors.StreamlitDuplicateElementKey: There are multiple elements with the same key='close_preview'. To fix this, please make sure that the key argument is unique for each element you create.

Traceback:
File "F:\REPOSITORIES\Saml1211\streamlit-stencil-search\local-api-server\venv\Lib\site-packages\streamlit\runtime\scriptrunner\exec_code.py", line 121, in exec_func_with_error_handling
    result = func()
             ^^^^^^
File "F:\REPOSITORIES\Saml1211\streamlit-stencil-search\local-api-server\venv\Lib\site-packages\streamlit\runtime\scriptrunner\script_runner.py", line 640, in code_to_exec
    exec(code, module.__dict__)
File "F:\REPOSITORIES\Saml1211\streamlit-stencil-search\app.py", line 332, in <module>
    health.main(selected_directory=selected_directory)
File "F:\REPOSITORIES\Saml1211\streamlit-stencil-search\modules\Stencil_Health.py", line 497, in main
    if st.button("Close Preview", key="close_preview"):
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# ... rest of traceback
```

## Cause

This error happens because Streamlit requires every interactive widget (like buttons) created during a single script run to have a unique `key`. The code was attempting to create a button with `key="close_preview"` in two different places:

1.  Within the `main` function of `modules/Stencil_Health.py` where the shape preview is displayed as part of the page content.
2.  Within the `render_shared_sidebar` function in `app/core/components.py`, which also contained logic to display the shape preview.

## Failed Automated Fix

Attempts were made to automatically edit `app/core/components.py` to remove the duplicate preview logic from the `render_shared_sidebar` function using the available tools. However, these attempts failed to apply the changes correctly, possibly due to issues with the editing tool or file state.

## Manual Fix Required

To resolve this, please perform the following manual edit:

1.  **Open the file:** `app/core/components.py`
2.  **Locate the function:** `render_shared_sidebar` (starts around line 125).
3.  **Find the preview section:** Inside this function, find the block of code responsible for displaying the shape preview. It likely starts with a comment like `# Show shape preview if selected` or similar, and contains the button `st.button("Close Preview", key="close_preview")`.
4.  **Delete the entire section:** Carefully delete the whole block of code related to displaying the shape preview *within the sidebar function*. Make sure you only remove the preview logic from *this* function and leave the preview logic in `modules/Stencil_Health.py` intact.
5.  **Verify structure:** Ensure the lines `st.markdown("---")` and `return selected_directory` remain at the end of the `render_shared_sidebar` function after removing the preview block.
6.  **Save** the file `app/core/components.py`.

After performing this manual edit, restart the Streamlit application (`.\start_streamlit.ps1`). The duplicate key error should be resolved. 