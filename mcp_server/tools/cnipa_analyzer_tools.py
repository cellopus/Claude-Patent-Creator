"""
CNIPA (China) Analyzer Tools

Provides automated analysis tools for Chinese patent applications:
- CNIPA formalities checking per Implementing Regulations of the Patent Law (PRC)
- CNIPA claims review per Art. 26.4 / Art. 25 Patent Law + Rules 21–23

Tools registered:
    - check_cnipa_formalities: Check CN formalities per Rules 17, 19, 20, 22, 24
    - review_cnipa_claims: Analyze claims for Art. 26.4 clarity/support and
        Art. 25 excluded subject matter (incl. diagnostic/treatment methods),
        plus Rule 21/22/23 checks
    - review_cnipa_specification: Analyze specification for Art. 26.3 sufficiency
        and Rule 17 description structure (incl. Summary "triple": technical
        problem + technical solution + beneficial effects)

Dependencies:
    - CNIPAFormalitiesChecker, CNIPAClaimsAnalyzer, CNIPASpecificationAnalyzer
    - mpep_index for retrieving relevant CN legal guidance
"""

from typing import Any, Optional


def register_cnipa_analyzer_tools(
    mcp,
    mpep_index,
    CNIPAFormalitiesChecker,
    CNIPAClaimsAnalyzer,
    CNIPASpecificationAnalyzer,
    log_info,
    log_warning,
    log_error,
    validate_input,
    CheckFormalitiesInput,
    ReviewClaimsInput,
    ReviewSpecificationInput,
    track_performance,
    log_operation_result,
):
    """Register CNIPA analyzer tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        mpep_index: Initialized MPEPIndex for retrieving CN legal guidance
        CNIPAFormalitiesChecker: Formalities-checker class (None if unavailable)
        CNIPAClaimsAnalyzer: Claims-analyzer class (None if unavailable)
        CNIPASpecificationAnalyzer: Spec-analyzer class (None if unavailable)
        log_info / log_warning / log_error: logging callables
        validate_input: input validation function
        CheckFormalitiesInput: Pydantic model for standard formalities fields
        ReviewClaimsInput: Pydantic model for claims review validation
        ReviewSpecificationInput: Pydantic model for spec review validation
        track_performance: performance tracking decorator
        log_operation_result: operation-result logger
    """

    @mcp.tool()
    @track_performance("tool_check_cnipa_formalities")
    def check_cnipa_formalities(
        abstract: Optional[str] = None,
        title: Optional[str] = None,
        specification: Optional[str] = None,
        claims_text: Optional[str] = None,
        drawings_present: bool = False,
        is_chembio: bool = False,
    ) -> dict[str, Any]:
        """Check CNIPA formalities per Implementing Regulations of the Patent Law (PRC).

        Covers Rule 17 (description sections and order), Rule 19 (drawings),
        Rule 20 (claim numbering), Rule 22 (multi-multi dependent claims
        prohibited), Rule 24 (abstract ≤300 CJK chars, single representative
        figure). Title limits per Rule 17(1): ≤25 CJK chars standard, ≤40
        for chemical/biotech inventions.

        Args:
            abstract: Abstract text (CN or EN translation).
            title: Application title.
            specification: Full specification text.
            claims_text: Numbered claims text (enables Rule 20 and Rule 22 checks).
            drawings_present: Whether drawings accompany the application.
            is_chembio: True for chemical/biotech inventions (raises title limit to 40 chars).
        """
        try:
            # Validate the shared subset (claims_text + is_chembio are CN-specific
            # passthroughs not on the standard Pydantic model)
            validated = validate_input(
                CheckFormalitiesInput,
                abstract=abstract,
                title=title,
                specification=specification,
                drawings_present=drawings_present,
            )
            abstract = validated.abstract
            title = validated.title
            specification = validated.specification
            drawings_present = validated.drawings_present

            # Light bound on claims_text without a dedicated model
            if claims_text is not None and len(claims_text) > 200000:
                return {"error": "Invalid input: claims_text exceeds 200000 characters"}

            log_info(
                "check_cnipa_formalities_started",
                has_abstract=abstract is not None,
                has_title=title is not None,
                has_spec=specification is not None,
                has_claims=claims_text is not None,
                is_chembio=is_chembio,
            )

            if CNIPAFormalitiesChecker:
                checker = CNIPAFormalitiesChecker()
                analysis_results = checker.check_all_formalities(
                    abstract=abstract,
                    title=title,
                    specification=specification,
                    claims_text=claims_text,
                    drawings_present=drawings_present,
                    is_chembio=is_chembio,
                )

                # Pull a few CN legal references for context
                cn_refs: list[dict[str, Any]] = []
                try:
                    cn_search = mpep_index.search(
                        "CN Implementing Regulations description abstract drawings claims Rule 17 22 24",
                        top_k=5,
                    )
                    for r in cn_search:
                        cn_refs.append(
                            {
                                "section": r["metadata"].get("section", ""),
                                "page": r["metadata"].get("page", 0),
                                "source": r["metadata"].get("source", ""),
                                "text": (
                                    r["text"][:500] + "..."
                                    if len(r["text"]) > 500
                                    else r["text"]
                                ),
                            }
                        )
                except Exception:
                    # CN sources may not be indexed yet — that's OK
                    pass

                result = {
                    "analysis_type": "automated",
                    "jurisdiction": "CN",
                    "overall_compliant": analysis_results["overall_compliant"],
                    "ready_to_file": analysis_results["compliance_summary"][
                        "ready_to_file"
                    ],
                    "summary": analysis_results["compliance_summary"]["summary"],
                    "critical_issues": analysis_results["compliance_summary"][
                        "critical_issues"
                    ],
                    "warnings": analysis_results["compliance_summary"]["warnings"],
                    "info": analysis_results["compliance_summary"]["info"],
                    "abstract": analysis_results["results"]["abstract"],
                    "title": analysis_results["results"]["title"],
                    "drawings": analysis_results["results"]["drawings"],
                    "sections": analysis_results["results"]["sections"],
                    "claims": analysis_results["results"]["claims"],
                    "issues": analysis_results["issues"],
                    "cn_references": cn_refs,
                }
                log_operation_result(
                    "check_cnipa_formalities", compliant=result["overall_compliant"]
                )
                return result

            log_warning(
                "CNIPAFormalitiesChecker not available — falling back to CN legal search"
            )
            try:
                search_results = mpep_index.search(
                    "CN Implementing Regulations formalities Rule 17 19 22 24", top_k=10
                )
                formatted = [
                    {
                        "section": r["metadata"].get("section", ""),
                        "page": r["metadata"].get("page", 0),
                        "source": r["metadata"].get("source", ""),
                        "text": r["text"],
                    }
                    for r in search_results
                ]
            except Exception as e:
                formatted = []
                log_warning(f"CN legal search fallback also failed: {e}")

            return {
                "analysis_type": "legal_search_only",
                "jurisdiction": "CN",
                "warning": (
                    "Automated CNIPA analysis unavailable — showing CN legal "
                    "references only. Ensure CN sources are indexed."
                ),
                "requirements": formatted,
            }

        except ValueError as e:
            log_error(
                "check_cnipa_formalities_validation_failed", exc_info=True, error=str(e)
            )
            return {"error": f"Invalid input: {str(e)}"}
        except Exception as e:
            log_error("check_cnipa_formalities_failed", exc_info=True)
            return {"error": f"CNIPA formalities check failed: {str(e)}"}

    @mcp.tool()
    @track_performance("tool_review_cnipa_claims")
    def review_cnipa_claims(claims_text: str) -> dict[str, Any]:
        """Analyze patent claims for CNIPA compliance.

        Checks Art. 26.4 Patent Law (clarity, support, conciseness),
        Art. 25 (excluded subject matter — incl. diagnostic/treatment methods,
        animal/plant varieties, nuclear transformation, mental-activity rules,
        printed-matter designs), Art. 5 (public interest / social morality),
        Rule 21 (essential technical features in independent claims),
        Rule 22 (no multi-multi dependent claims), and Rule 23 (recommended
        two-part form using 其特征在于 / 'characterised in that').
        """
        try:
            validated = validate_input(ReviewClaimsInput, claims_text=claims_text)
            claims_text = validated.claims_text

            log_info("review_cnipa_claims_started", claims_length=len(claims_text))

            if CNIPAClaimsAnalyzer:
                analyzer = CNIPAClaimsAnalyzer()
                analysis_results = analyzer.analyze_claims(claims_text)

                cn_refs: list[dict[str, Any]] = []
                try:
                    cn_search = mpep_index.search(
                        "Art. 26.4 Patent Law claim clarity support Art. 25 excluded "
                        "subject matter Rule 22 multi-dependent",
                        top_k=5,
                    )
                    for r in cn_search:
                        cn_refs.append(
                            {
                                "section": r["metadata"].get("section", ""),
                                "page": r["metadata"].get("page", 0),
                                "source": r["metadata"].get("source", ""),
                                "text": (
                                    r["text"][:500] + "..."
                                    if len(r["text"]) > 500
                                    else r["text"]
                                ),
                            }
                        )
                except Exception:
                    pass

                result = {
                    "analysis_type": "automated",
                    "jurisdiction": "CN",
                    "claim_count": analysis_results["claim_count"],
                    "independent_claims": analysis_results["independent_count"],
                    "dependent_claims": analysis_results["dependent_count"],
                    "multi_dependent_claims": analysis_results.get(
                        "multi_dependent_count", 0
                    ),
                    "compliance_score": analysis_results["compliance_score"],
                    "total_issues": analysis_results["total_issues"],
                    "critical_issues": analysis_results["critical_issues"],
                    "important_issues": analysis_results["important_issues"],
                    "minor_issues": analysis_results["minor_issues"],
                    "issues_by_type": analysis_results["issues_by_type"],
                    "summary": analysis_results["summary"],
                    "issues": analysis_results["issues"],
                    "cn_references": cn_refs,
                }
                log_operation_result(
                    "review_cnipa_claims", total_issues=result["total_issues"]
                )
                return result

            log_warning(
                "CNIPAClaimsAnalyzer not available — falling back to CN legal search"
            )
            try:
                search_results = mpep_index.search(
                    "CN Patent Law Art. 26.4 Art. 25 claim clarity excluded subject matter",
                    top_k=10,
                )
                formatted = [
                    {
                        "section": r["metadata"].get("section", ""),
                        "page": r["metadata"].get("page", 0),
                        "source": r["metadata"].get("source", ""),
                        "text": r["text"],
                    }
                    for r in search_results
                ]
            except Exception as e:
                formatted = []
                log_warning(f"CN legal search fallback failed: {e}")

            return {
                "analysis_type": "legal_search_only",
                "jurisdiction": "CN",
                "warning": (
                    "Automated CNIPA analysis unavailable — showing CN legal "
                    "references only. Ensure CN sources are indexed."
                ),
                "requirements": formatted,
            }

        except ValueError as e:
            log_error(
                "review_cnipa_claims_validation_failed", exc_info=True, error=str(e)
            )
            return {"error": f"Invalid input: {str(e)}"}
        except Exception as e:
            log_error("review_cnipa_claims_failed", exc_info=True)
            return {"error": f"CNIPA claims review failed: {str(e)}"}

    @mcp.tool()
    @track_performance("tool_review_cnipa_specification")
    def review_cnipa_specification(
        claims_text: str, specification: str
    ) -> dict[str, Any]:
        """Analyze the description for Art. 26.3 sufficiency and Rule 17 structure.

        Checks:
        - Rule 17 required sections (Technical field / Background / Summary /
          Brief description of drawings / Detailed description) AND their canonical order
        - The Summary "triple" examiners look for: technical problem,
          technical solution, and beneficial effects must all be present
        - At least one detailed embodiment / example
        - Reference-sign consistency between description and drawings (heuristic)
        - Art. 26.3 sufficiency: each independent-claim element appears in the
          description with adequate detail
        - Functional-language sufficiency ("configured to ...")
        """
        try:
            validated = validate_input(
                ReviewSpecificationInput,
                claims_text=claims_text,
                specification=specification,
            )
            claims_text = validated.claims_text
            specification = validated.specification

            log_info(
                "review_cnipa_specification_started",
                claims_length=len(claims_text),
                spec_length=len(specification),
            )

            if CNIPAClaimsAnalyzer and CNIPASpecificationAnalyzer:
                claims_analyzer = CNIPAClaimsAnalyzer()
                parsed_claims = claims_analyzer._parse_claims(claims_text)

                spec_analyzer = CNIPASpecificationAnalyzer()
                analysis_results = spec_analyzer.analyze_specification_support(
                    parsed_claims, specification
                )

                cn_refs: list[dict[str, Any]] = []
                try:
                    cn_search = mpep_index.search(
                        "Art. 26.3 Patent Law sufficiency disclosure Rule 17 "
                        "description structure technical problem solution effects",
                        top_k=5,
                    )
                    for r in cn_search:
                        cn_refs.append(
                            {
                                "section": r["metadata"].get("section", ""),
                                "page": r["metadata"].get("page", 0),
                                "source": r["metadata"].get("source", ""),
                                "text": (
                                    r["text"][:500] + "..."
                                    if len(r["text"]) > 500
                                    else r["text"]
                                ),
                            }
                        )
                except Exception:
                    pass

                result = {
                    "analysis_type": "automated",
                    "jurisdiction": "CN",
                    "specification_paragraphs": analysis_results[
                        "specification_paragraphs"
                    ],
                    "indexed_terms": analysis_results["indexed_terms"],
                    "total_issues": analysis_results["total_issues"],
                    "critical_issues": analysis_results["critical_issues"],
                    "important_issues": analysis_results["important_issues"],
                    "sufficiency_issues": analysis_results["sufficiency_issues"],
                    "section_issues": analysis_results["section_issues"],
                    "summary_triple_issues": analysis_results.get(
                        "summary_triple_issues", 0
                    ),
                    "embodiment_issues": analysis_results.get("embodiment_issues", 0),
                    "reference_sign_issues": analysis_results.get(
                        "reference_sign_issues", 0
                    ),
                    "spec_coverage": analysis_results["spec_coverage"],
                    "summary": analysis_results["summary"],
                    "compliant": analysis_results["compliant"],
                    "issues": analysis_results["issues"],
                    "input_warnings": analysis_results.get("input_warnings", []),
                    "cn_references": cn_refs,
                }
                log_operation_result(
                    "review_cnipa_specification",
                    total_issues=result["total_issues"],
                )
                return result

            log_warning(
                "CNIPASpecificationAnalyzer not available — falling back to CN legal search"
            )
            try:
                search_results = mpep_index.search(
                    "Art. 26.3 Patent Law sufficiency Rule 17 description CN",
                    top_k=10,
                )
                formatted = [
                    {
                        "section": r["metadata"].get("section", ""),
                        "page": r["metadata"].get("page", 0),
                        "source": r["metadata"].get("source", ""),
                        "text": r["text"],
                    }
                    for r in search_results
                ]
            except Exception as e:
                formatted = []
                log_warning(f"CN legal search fallback failed: {e}")

            return {
                "analysis_type": "legal_search_only",
                "jurisdiction": "CN",
                "warning": (
                    "Automated CNIPA specification analysis unavailable — showing "
                    "CN legal references only. Ensure CN sources are indexed."
                ),
                "guidance": formatted,
            }

        except ValueError as e:
            log_error(
                "review_cnipa_specification_validation_failed",
                exc_info=True,
                error=str(e),
            )
            return {"error": f"Invalid input: {str(e)}"}
        except Exception as e:
            log_error("review_cnipa_specification_failed", exc_info=True)
            return {"error": f"CNIPA specification review failed: {str(e)}"}
