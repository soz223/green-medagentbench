from __future__ import annotations

from typing import List
import requests

from green_agent.protocol import (
    ToolSpec,
    ToolCallAction,
)


class MedAgentEnvAdapter:
    """
    FHIR-based environment adapter for the Green Agent.

    This adapter exposes medical tools that interact with a local FHIR server.
    It translates FHIR responses into human-readable English summaries that
    LLM agents can understand and reason with.

    The adapter provides tools for:
    - Patient demographics
    - Laboratory results
    - Medical conditions/diagnoses
    - Encounters (hospital visits, outpatient visits)
    - Medications
    - Procedures
    - Observations (vital signs, measurements)
    - Diagnostic reports

    All tool methods return English text summaries, not raw JSON.
    """

    def __init__(self, fhir_base_url: str = "http://localhost:8080/fhir"):
        """
        Initialize the FHIR environment adapter.

        Args:
            fhir_base_url: Base URL of the FHIR server (default: localhost:8080/fhir)
        """
        self.fhir_base_url = fhir_base_url
        self.session = requests.Session()

    # ---------- Public API: List available tools ----------

    def list_available_tools(self) -> List[ToolSpec]:
        """
        Return the list of available FHIR tools.

        This list is exposed to the agent via Observations.
        Tool names must match exactly with tool_name in ToolCallAction.

        Returns:
            List of ToolSpec objects describing available tools
        """
        return [
            ToolSpec(
                name="get_patient_basic",
                description="Retrieve basic patient information including name, gender, and birth date.",
            ),
            ToolSpec(
                name="get_recent_labs",
                description="Retrieve recent laboratory results for a specific lab code (e.g., Hb, Cr, GLU, MG).",
            ),
            ToolSpec(
                name="get_conditions",
                description="Retrieve current and past medical diagnoses (conditions) for the patient.",
            ),
            ToolSpec(
                name="search_encounters",
                description="Search hospital visits and outpatient encounters for the patient.",
            ),
            ToolSpec(
                name="search_medications",
                description="Search current and past medications for the patient.",
            ),
            ToolSpec(
                name="search_procedures",
                description="Search medical procedures performed for the patient.",
            ),
            ToolSpec(
                name="search_observations",
                description="Search observations for the patient, optionally filtered by category (e.g., vital-signs, laboratory).",
            ),
            ToolSpec(
                name="search_diagnostic_reports",
                description="Search diagnostic reports including imaging studies and test results.",
            ),
            ToolSpec(
                name="post_fhir_resource",
                description="Create a new FHIR resource by POSTing to the FHIR server. Use this to create Observations, MedicationRequests, ServiceRequests, etc. Requires resource_type (e.g., 'Observation') and payload (complete FHIR resource as dict).",
            ),
        ]

    # ---------- Public API: Handle tool calls ----------

    def handle_tool_call(self, action: ToolCallAction) -> str:
        """
        Execute a tool call and return a human-readable result.

        This is the main entry point called by EpisodeManager.
        It dispatches to specific tool methods based on tool_name.

        Args:
            action: ToolCallAction specifying which tool to call and with what arguments

        Returns:
            English text summary of the tool execution result
        """
        name = action.tool_name
        args = action.arguments or {}

        # Dispatch to appropriate tool method
        if name == "get_patient_basic":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'get_patient_basic' requires argument 'patient_id'."
            return self._tool_get_patient_basic(patient_id)

        elif name == "get_recent_labs":
            patient_id = args.get("patient_id")
            lab_code = args.get("lab_code")
            if not patient_id or not lab_code:
                return "Error: Tool 'get_recent_labs' requires arguments 'patient_id' and 'lab_code'."
            return self._tool_get_recent_labs(patient_id, lab_code)

        elif name == "get_conditions":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'get_conditions' requires argument 'patient_id'."
            return self._tool_get_conditions(patient_id)

        elif name == "search_encounters":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'search_encounters' requires argument 'patient_id'."
            return self._tool_search_encounters(patient_id)

        elif name == "search_medications":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'search_medications' requires argument 'patient_id'."
            return self._tool_search_medications(patient_id)

        elif name == "search_procedures":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'search_procedures' requires argument 'patient_id'."
            return self._tool_search_procedures(patient_id)

        elif name == "search_observations":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'search_observations' requires argument 'patient_id'."
            category = args.get("category")  # Optional
            return self._tool_search_observations(patient_id, category)

        elif name == "search_diagnostic_reports":
            patient_id = args.get("patient_id")
            if not patient_id:
                return "Error: Tool 'search_diagnostic_reports' requires argument 'patient_id'."
            return self._tool_search_diagnostic_reports(patient_id)

        elif name == "post_fhir_resource":
            resource_type = args.get("resource_type")
            payload = args.get("payload")
            if not resource_type or not payload:
                return "Error: Tool 'post_fhir_resource' requires arguments 'resource_type' and 'payload'."
            return self._tool_post_fhir_resource(resource_type, payload)

        else:
            available = [t.name for t in self.list_available_tools()]
            return f"Error: Unknown tool '{name}'. Available tools: {available}"

    # ---------- Tool implementations ----------

    def _tool_get_patient_basic(self, patient_id: str) -> str:
        """
        Retrieve basic patient demographics.

        FHIR Endpoint: GET /Patient/{id}

        Args:
            patient_id: The patient's medical record number (MRN)

        Returns:
            English summary of patient demographics
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server. This typically means the patient does not exist in the system."

        url = f"{self.fhir_base_url}/Patient/{patient_id}"

        try:
            resp = self.session.get(url, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve patient information. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        # Extract patient name
        name = ""
        if "name" in data and data["name"]:
            n = data["name"][0]
            given = " ".join(n.get("given", []))
            family = n.get("family", "")
            name = f"{given} {family}".strip()

        gender = data.get("gender", "unknown")
        birth_date = data.get("birthDate", "unknown")

        return (
            f"Patient Basic Information:\n"
            f"- ID (MRN): {patient_id}\n"
            f"- Name: {name or 'unknown'}\n"
            f"- Gender: {gender}\n"
            f"- Birth Date: {birth_date}\n"
        )

    def _tool_get_recent_labs(self, patient_id: str, lab_code: str) -> str:
        """
        Retrieve recent laboratory results for a specific code.

        FHIR Endpoint: GET /Observation?subject=Patient/{id}&code={lab_code}

        Args:
            patient_id: The patient's MRN
            lab_code: The laboratory code (e.g., "Hb", "GLU", "MG")

        Returns:
            English summary of recent lab results with values and timestamps
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {
            "subject": f"Patient/{patient_id}",
            "code": lab_code,
            "_sort": "-date",
            "_count": "10",
        }
        url = f"{self.fhir_base_url}/Observation"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve lab results. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            return f"No lab results found for patient {patient_id} with code {lab_code}."

        lines = [f"Recent lab results for patient {patient_id} (code: {lab_code}):"]
        for e in entries:
            res = e.get("resource", {})
            value = None
            unit = ""

            # Extract value from different possible fields
            if "valueQuantity" in res:
                value = res["valueQuantity"].get("value")
                unit = res["valueQuantity"].get("unit", "")
            elif "valueString" in res:
                value = res["valueString"]

            # Extract timestamp
            eff_time = res.get("effectiveDateTime") or res.get("issued") or "unknown time"

            if value is not None:
                lines.append(f"  - {eff_time}: {value} {unit}".strip())
            else:
                lines.append(f"  - {eff_time}: (no structured value available)")

        return "\n".join(lines)

    def _tool_get_conditions(self, patient_id: str) -> str:
        """
        Retrieve medical diagnoses/conditions for the patient.

        FHIR Endpoint: GET /Condition?subject=Patient/{id}

        Args:
            patient_id: The patient's MRN

        Returns:
            English summary of diagnoses with onset/recorded dates
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {"subject": f"Patient/{patient_id}"}
        url = f"{self.fhir_base_url}/Condition"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve conditions. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            return f"No conditions found for patient {patient_id}."

        lines = [f"Medical conditions for patient {patient_id}:"]
        for e in entries:
            res = e.get("resource", {})
            code = res.get("code", {})

            # Extract condition text/display
            text = code.get("text")
            if not text and "coding" in code and code["coding"]:
                c0 = code["coding"][0]
                text = c0.get("display") or c0.get("code")

            # Extract onset/recorded date
            onset = res.get("onsetDateTime") or res.get("recordedDate") or "unknown date"

            lines.append(f"  - {text or 'unknown diagnosis'} (onset/recorded: {onset})")

        return "\n".join(lines)

    def _tool_search_encounters(self, patient_id: str) -> str:
        """
        Search encounters (hospital visits, outpatient encounters).

        FHIR Endpoint: GET /Encounter?subject=Patient/{id}

        Args:
            patient_id: The patient's MRN

        Returns:
            English summary of encounters with types, periods, and status
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {
            "subject": f"Patient/{patient_id}",
            "_sort": "-date",
            "_count": "10"
        }
        url = f"{self.fhir_base_url}/Encounter"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve encounters. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            return f"No encounters found for patient {patient_id}."

        lines = [f"Encounters for patient {patient_id}:"]
        for e in entries:
            res = e.get("resource", {})

            # Extract encounter type
            enc_type = "unknown type"
            if "type" in res and res["type"]:
                type_obj = res["type"][0]
                if "coding" in type_obj and type_obj["coding"]:
                    enc_type = type_obj["coding"][0].get("display") or type_obj["coding"][0].get("code", "unknown type")
                elif "text" in type_obj:
                    enc_type = type_obj["text"]

            # Extract period
            period = res.get("period", {})
            start = period.get("start", "unknown")
            end = period.get("end", "ongoing")

            # Extract status
            status = res.get("status", "unknown")

            lines.append(f"  - {enc_type} | Period: {start} to {end} | Status: {status}")

        return "\n".join(lines)

    def _tool_search_medications(self, patient_id: str) -> str:
        """
        Search medication requests/statements for the patient.

        FHIR Endpoint: GET /MedicationRequest?subject=Patient/{id}

        Args:
            patient_id: The patient's MRN

        Returns:
            English summary of medications with status and dates
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {
            "subject": f"Patient/{patient_id}",
            "_sort": "-authoredon",
            "_count": "10"
        }
        url = f"{self.fhir_base_url}/MedicationRequest"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve medications. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            return f"No medication requests found for patient {patient_id}."

        lines = [f"Medications for patient {patient_id}:"]
        for e in entries:
            res = e.get("resource", {})

            # Extract medication name
            med_name = "unknown medication"
            if "medicationCodeableConcept" in res:
                med_concept = res["medicationCodeableConcept"]
                med_name = med_concept.get("text")
                if not med_name and "coding" in med_concept and med_concept["coding"]:
                    med_name = med_concept["coding"][0].get("display") or med_concept["coding"][0].get("code", "unknown")

            # Extract status and date
            status = res.get("status", "unknown")
            authored_on = res.get("authoredOn", "unknown date")

            lines.append(f"  - {med_name} | Status: {status} | Authored: {authored_on}")

        return "\n".join(lines)

    def _tool_search_procedures(self, patient_id: str) -> str:
        """
        Search procedures performed for the patient.

        FHIR Endpoint: GET /Procedure?subject=Patient/{id}

        Args:
            patient_id: The patient's MRN

        Returns:
            English summary of procedures with dates and status
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {
            "subject": f"Patient/{patient_id}",
            "_sort": "-date",
            "_count": "10"
        }
        url = f"{self.fhir_base_url}/Procedure"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve procedures. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            return f"No procedures found for patient {patient_id}."

        lines = [f"Procedures for patient {patient_id}:"]
        for e in entries:
            res = e.get("resource", {})

            # Extract procedure name
            proc_name = "unknown procedure"
            if "code" in res:
                code_obj = res["code"]
                proc_name = code_obj.get("text")
                if not proc_name and "coding" in code_obj and code_obj["coding"]:
                    proc_name = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code", "unknown")

            # Extract performed date and status
            performed = res.get("performedDateTime") or res.get("performedPeriod", {}).get("start", "unknown date")
            status = res.get("status", "unknown")

            lines.append(f"  - {proc_name} | Performed: {performed} | Status: {status}")

        return "\n".join(lines)

    def _tool_search_observations(self, patient_id: str, category: str = None) -> str:
        """
        Search observations for the patient, optionally filtered by category.

        FHIR Endpoint: GET /Observation?subject=Patient/{id}&category={category}

        Args:
            patient_id: The patient's MRN
            category: Optional category filter (e.g., "vital-signs", "laboratory")

        Returns:
            English summary of observations with values and timestamps
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {
            "subject": f"Patient/{patient_id}",
            "_sort": "-date",
            "_count": "10"
        }
        if category:
            params["category"] = category

        url = f"{self.fhir_base_url}/Observation"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve observations. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            category_str = f" (category: {category})" if category else ""
            return f"No observations found for patient {patient_id}{category_str}."

        category_str = f" (category: {category})" if category else ""
        lines = [f"Observations for patient {patient_id}{category_str}:"]

        for e in entries:
            res = e.get("resource", {})

            # Extract observation code/name
            obs_name = "unknown observation"
            if "code" in res:
                code_obj = res["code"]
                obs_name = code_obj.get("text")
                if not obs_name and "coding" in code_obj and code_obj["coding"]:
                    obs_name = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code", "unknown")

            # Extract value
            value = None
            unit = ""
            if "valueQuantity" in res:
                value = res["valueQuantity"].get("value")
                unit = res["valueQuantity"].get("unit", "")
            elif "valueString" in res:
                value = res["valueString"]
            elif "valueCodeableConcept" in res:
                value_concept = res["valueCodeableConcept"]
                value = value_concept.get("text")
                if not value and "coding" in value_concept and value_concept["coding"]:
                    value = value_concept["coding"][0].get("display", "coded value")

            # Extract timestamp
            eff_time = res.get("effectiveDateTime") or res.get("issued") or "unknown time"

            if value is not None:
                lines.append(f"  - {obs_name}: {value} {unit} | Time: {eff_time}".strip())
            else:
                lines.append(f"  - {obs_name}: (no value available) | Time: {eff_time}")

        return "\n".join(lines)

    def _tool_search_diagnostic_reports(self, patient_id: str) -> str:
        """
        Search diagnostic reports including imaging and test results.

        FHIR Endpoint: GET /DiagnosticReport?subject=Patient/{id}

        Args:
            patient_id: The patient's MRN

        Returns:
            English summary of diagnostic reports with conclusions
        """
        if patient_id == "UNKNOWN":
            return "Patient ID is unknown. Cannot query FHIR server."

        params = {
            "subject": f"Patient/{patient_id}",
            "_sort": "-date",
            "_count": "10"
        }
        url = f"{self.fhir_base_url}/DiagnosticReport"

        try:
            resp = self.session.get(url, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        if resp.status_code != 200:
            return f"Error: Failed to retrieve diagnostic reports. Status={resp.status_code}, Response={resp.text[:200]}"

        try:
            data = resp.json()
        except ValueError:
            return "Error: Invalid JSON response from FHIR server."

        entries = data.get("entry", [])

        if not entries:
            return f"No diagnostic reports found for patient {patient_id}."

        lines = [f"Diagnostic reports for patient {patient_id}:"]
        for e in entries:
            res = e.get("resource", {})

            # Extract report name/code
            report_name = "unknown report"
            if "code" in res:
                code_obj = res["code"]
                report_name = code_obj.get("text")
                if not report_name and "coding" in code_obj and code_obj["coding"]:
                    report_name = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code", "unknown")

            # Extract status, date, and conclusion
            status = res.get("status", "unknown")
            issued = res.get("issued") or res.get("effectiveDateTime", "unknown date")
            conclusion = res.get("conclusion", "no conclusion available")

            # Truncate long conclusions
            if len(conclusion) > 100:
                conclusion = conclusion[:97] + "..."

            lines.append(f"  - {report_name} | Status: {status} | Issued: {issued}")
            lines.append(f"    Conclusion: {conclusion}")

        return "\n".join(lines)

    def _tool_post_fhir_resource(self, resource_type: str, payload: dict) -> str:
        """
        Create a new FHIR resource via POST request.

        FHIR Endpoint: POST /{resource_type}

        This tool enables creating new FHIR resources such as:
        - Observation (vital signs, lab results)
        - MedicationRequest (medication orders)
        - ServiceRequest (lab tests, referrals, procedures)

        Args:
            resource_type: The FHIR resource type (e.g., "Observation", "MedicationRequest", "ServiceRequest")
            payload: Complete FHIR resource as a dictionary

        Returns:
            English summary of the POST result (success or error)
        """
        # Construct the URL for the POST request
        url = f"{self.fhir_base_url}/{resource_type}"

        try:
            # Send POST request with JSON payload
            resp = self.session.post(url, json=payload, timeout=10)
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to FHIR server: {str(e)}"

        # Check response status
        if resp.status_code in (200, 201):
            # Success - extract resource ID if available
            try:
                result_data = resp.json()
                resource_id = result_data.get("id", "unknown")
                return f"Success: Created {resource_type} with ID {resource_id}. Status code: {resp.status_code}"
            except ValueError:
                return f"Success: Created {resource_type}. Status code: {resp.status_code} (response not JSON)"
        else:
            # Failed POST
            error_text = resp.text[:200] if resp.text else "No error message"
            return f"Error: Failed to create {resource_type}. Status={resp.status_code}, Response={error_text}"
