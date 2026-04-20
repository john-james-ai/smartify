#!/usr/bin/env python3
# ================================================================================================ #
# Project    : Smartify                                                                            #
# Description: Deep Learning and Generative AI Smartify Lab                                        #
# Version    : 0.1.0                                                                               #
# Python     : 3.14.3                                                                              #
# Filepath   : /smartify/agentic_development/mcp                                                   #
# Filename   : mcp_server.py                                                                       #
# ------------------------------------------------------------------------------------------------ #
# Author     : John James                                                                          #
# Email      : john@variancexplained.ai                                                            #
# URL        : https://github.com/john-james-ai/smartify                                           #
# ------------------------------------------------------------------------------------------------ #
# Created    : Sunday April 19th 2026 10:32:16 pm                                                  #
# Modified   : Monday April 20th 2026 09:44:07 am                                                  #
# ------------------------------------------------------------------------------------------------ #
# License    : MIT License                                                                         #
# Copyright  : (c) 2026 John James                                                                 #
# ================================================================================================ #

"""MCP server exposing document tools, resources, and prompts."""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

@mcp.tool(
    name="read_doc",
    description="Read the contents of a document.",
)
def read_doc(doc_id: str = Field(description="Id of Document to read")) -> str:
    """Read the contents of a document.

    Args:
        doc_id: The ID of the document to read.

    Returns:
        The content of the requested document.

    Raises:
        ValueError: If the document with the specified ID is not found.
    """
    if doc_id not in docs:
        raise ValueError(f"Document with id '{doc_id}' not found.")
    return docs[doc_id]

@mcp.tool(
    name="edit_doc",
    description="Edit the contents of a document.",
)
def edit_doc(doc_id: str = Field(description="Id of Document to edit"),
             old_str: str = Field(description="Old content to replace"),
             new_str: str = Field(description="New content for the document")) -> str:
    """Replace text within a document.

    Args:
        doc_id: The ID of the document to update.
        old_str: The existing content to replace.
        new_str: The replacement content.

    Returns:
        A confirmation message indicating the document was updated.

    Raises:
        ValueError: If the document is not found or the target text is absent.
    """
    if doc_id not in docs:
        raise ValueError(f"Document with id '{doc_id}' not found.")
    if old_str not in docs[doc_id]:
        raise ValueError(f"Old content '{old_str}' not found in document '{doc_id}'.")
    docs[doc_id] = docs[doc_id].replace(old_str, new_str)
    return f"Document '{doc_id}' has been updated."

@mcp.resource("docs//documents", mime_type="application/json")
def list_docs() -> list[str]:
    """List all available document IDs.

    Returns:
        A list of document IDs.
    """
    return list(docs.keys())


@mcp.resource("docs//documents/{doc_id}", mime_type="text/plain")
def get_doc(doc_id: str) -> str:
    """Get the content of a specific document.

    Args:
        doc_id: The ID of the document to retrieve.

    Returns:
        The content of the specified document.

    Raises:
        ValueError: If the document with the specified ID is not found.
    """
    if doc_id not in docs:
        raise ValueError(f"Document with id '{doc_id}' not found.")
    return docs[doc_id]


@mcp.prompt(name="format", description="Rewrites a document in a markdown format.")
def format_doc(doc_id: str = Field(description="Id of Document to format")) -> list[base.Message]:
    """Create a prompt that rewrites a document in Markdown.

    Args:
        doc_id: The ID of the document to format.

    Returns:
        A single prompt message instructing the model to rewrite the document.
    """
    prompt = f"""Rewrite the document in a markdown format.

    The id of the document is:
    <document_id>
    {doc_id}
    </document_id>

    Add in headers, bullet points, and other markdown formatting as appropriate to make the document easier to read. Use the 'edit_doc' tool to edit the document.
    """
    return [base.Message(prompt)]


# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
