#!/usr/bin/env python3
"""
ComBadge System Requirements Validator

Comprehensive system requirements checking and validation for enterprise deployment.
Validates hardware, software, and network requirements before installation.
"""

import os
import sys
import platform
import psutil
import subprocess
import socket
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class RequirementLevel(Enum):
    """Requirement severity levels."""
    CRITICAL = "critical"
    RECOMMENDED = "recommended" 
    OPTIONAL = "optional"


@dataclass
class SystemRequirement:
    """Individual system requirement definition."""
    name: str
    description: str
    level: RequirementLevel
    check_function: str
    minimum_value: Any = None
    recommended_value: Any = None
    unit: str = ""


@dataclass
class RequirementResult:
    """Result of a requirement check."""
    requirement: SystemRequirement
    passed: bool
    current_value: Any
    message: str
    details: Optional[Dict] = None


class SystemRequirementsChecker:
    """Comprehensive system requirements validation."""
    
    def __init__(self):
        """Initialize requirements checker."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.requirements = self._define_requirements()
        
    def _define_requirements(self) -> List[SystemRequirement]:
        """Define all system requirements for ComBadge."""
        return [
            # Critical Hardware Requirements
            SystemRequirement(
                name="total_ram",
                description="Total System RAM",
                level=RequirementLevel.CRITICAL,
                check_function="check_ram",
                minimum_value=8,
                recommended_value=16,
                unit="GB"
            ),
            SystemRequirement(
                name="available_ram",
                description="Available System RAM",
                level=RequirementLevel.CRITICAL,
                check_function="check_available_ram",
                minimum_value=6,
                recommended_value=12,
                unit="GB"
            ),
            SystemRequirement(
                name="disk_space",
                description="Available Disk Space",
                level=RequirementLevel.CRITICAL,
                check_function="check_disk_space",
                minimum_value=10,
                recommended_value=50,
                unit="GB"
            ),
            SystemRequirement(
                name="cpu_cores",
                description="CPU Core Count",
                level=RequirementLevel.CRITICAL,
                check_function="check_cpu_cores",
                minimum_value=4,
                recommended_value=8,
                unit="cores"
            ),
            SystemRequirement(
                name="cpu_frequency",
                description="CPU Base Frequency",
                level=RequirementLevel.RECOMMENDED,
                check_function="check_cpu_frequency",
                minimum_value=2.0,
                recommended_value=3.0,
                unit="GHz"
            ),
            
            # Operating System Requirements
            SystemRequirement(
                name="windows_version",
                description="Windows Version",
                level=RequirementLevel.CRITICAL,
                check_function="check_windows_version",
                minimum_value="10.0",
                recommended_value="11.0",
                unit=""
            ),
            SystemRequirement(
                name="architecture",
                description="System Architecture",
                level=RequirementLevel.CRITICAL,
                check_function="check_architecture",
                minimum_value="64bit",
                unit=""
            ),
            
            # Software Requirements
            SystemRequirement(
                name="python_version",
                description="Python Version (if using source)",
                level=RequirementLevel.OPTIONAL,
                check_function="check_python_version",
                minimum_value="3.9",
                recommended_value="3.11",
                unit=""
            ),
            
            # Network Requirements
            SystemRequirement(
                name="internet_connectivity",
                description="Internet Connectivity",
                level=RequirementLevel.RECOMMENDED,
                check_function="check_internet_connectivity",
                unit=""
            ),
            SystemRequirement(
                name="dns_resolution",
                description="DNS Resolution",
                level=RequirementLevel.RECOMMENDED,
                check_function="check_dns_resolution",
                unit=""
            ),
            
            # GPU Requirements (Optional)
            SystemRequirement(
                name="gpu_memory",
                description="GPU Memory (for acceleration)",
                level=RequirementLevel.OPTIONAL,
                check_function="check_gpu_memory",
                minimum_value=4,
                recommended_value=8,
                unit="GB"
            ),
            
            # Security Requirements
            SystemRequirement(
                name="windows_defender",
                description="Windows Defender Status",
                level=RequirementLevel.RECOMMENDED,
                check_function="check_windows_defender",
                unit=""
            ),
            SystemRequirement(
                name="execution_policy",
                description="PowerShell Execution Policy",
                level=RequirementLevel.OPTIONAL,
                check_function="check_execution_policy",
                unit=""
            )
        ]
    
    def check_ram(self, requirement: SystemRequirement) -> RequirementResult:
        """Check total system RAM."""
        try:
            total_ram_bytes = psutil.virtual_memory().total
            total_ram_gb = total_ram_bytes / (1024**3)
            
            passed = total_ram_gb >= requirement.minimum_value
            
            if total_ram_gb >= requirement.recommended_value:
                message = f"Excellent: {total_ram_gb:.1f} GB RAM available"
            elif passed:
                message = f"Adequate: {total_ram_gb:.1f} GB RAM (minimum met)"
            else:
                message = f"Insufficient: {total_ram_gb:.1f} GB RAM (minimum: {requirement.minimum_value} GB)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=round(total_ram_gb, 1),
                message=message,
                details={"bytes": total_ram_bytes}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check RAM: {e}"
            )
    
    def check_available_ram(self, requirement: SystemRequirement) -> RequirementResult:
        """Check available system RAM."""
        try:
            memory_info = psutil.virtual_memory()
            available_ram_gb = memory_info.available / (1024**3)
            
            passed = available_ram_gb >= requirement.minimum_value
            
            if available_ram_gb >= requirement.recommended_value:
                message = f"Excellent: {available_ram_gb:.1f} GB RAM available"
            elif passed:
                message = f"Adequate: {available_ram_gb:.1f} GB RAM available"
            else:
                message = f"Low memory: {available_ram_gb:.1f} GB available (minimum: {requirement.minimum_value} GB)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=round(available_ram_gb, 1),
                message=message,
                details={"percent_used": memory_info.percent}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check available RAM: {e}"
            )
    
    def check_disk_space(self, requirement: SystemRequirement) -> RequirementResult:
        """Check available disk space."""
        try:
            # Check space on C: drive (typical installation location)
            disk_usage = psutil.disk_usage('C:\\' if platform.system() == 'Windows' else '/')
            free_space_gb = disk_usage.free / (1024**3)
            
            passed = free_space_gb >= requirement.minimum_value
            
            if free_space_gb >= requirement.recommended_value:
                message = f"Excellent: {free_space_gb:.1f} GB free disk space"
            elif passed:
                message = f"Adequate: {free_space_gb:.1f} GB free disk space"
            else:
                message = f"Insufficient: {free_space_gb:.1f} GB free (minimum: {requirement.minimum_value} GB)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=round(free_space_gb, 1),
                message=message,
                details={"total_gb": round(disk_usage.total / (1024**3), 1)}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check disk space: {e}"
            )
    
    def check_cpu_cores(self, requirement: SystemRequirement) -> RequirementResult:
        """Check CPU core count."""
        try:
            cpu_cores = psutil.cpu_count(logical=False)  # Physical cores
            logical_cores = psutil.cpu_count(logical=True)
            
            passed = cpu_cores >= requirement.minimum_value
            
            if cpu_cores >= requirement.recommended_value:
                message = f"Excellent: {cpu_cores} CPU cores ({logical_cores} logical)"
            elif passed:
                message = f"Adequate: {cpu_cores} CPU cores ({logical_cores} logical)"
            else:
                message = f"Insufficient: {cpu_cores} CPU cores (minimum: {requirement.minimum_value})"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=cpu_cores,
                message=message,
                details={"logical_cores": logical_cores}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check CPU cores: {e}"
            )
    
    def check_cpu_frequency(self, requirement: SystemRequirement) -> RequirementResult:
        """Check CPU frequency."""
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq is None:
                return RequirementResult(
                    requirement=requirement,
                    passed=True,  # Can't determine, assume OK
                    current_value=None,
                    message="CPU frequency information not available"
                )
            
            max_freq_ghz = cpu_freq.max / 1000.0 if cpu_freq.max else cpu_freq.current / 1000.0
            
            passed = max_freq_ghz >= requirement.minimum_value
            
            if max_freq_ghz >= requirement.recommended_value:
                message = f"Excellent: {max_freq_ghz:.1f} GHz CPU frequency"
            elif passed:
                message = f"Adequate: {max_freq_ghz:.1f} GHz CPU frequency"
            else:
                message = f"Low: {max_freq_ghz:.1f} GHz CPU (recommended: {requirement.recommended_value} GHz)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=round(max_freq_ghz, 1),
                message=message,
                details={"current_ghz": round(cpu_freq.current / 1000.0, 1)}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=True,  # Non-critical failure
                current_value=None,
                message=f"Could not determine CPU frequency: {e}"
            )
    
    def check_windows_version(self, requirement: SystemRequirement) -> RequirementResult:
        """Check Windows version."""
        try:
            if platform.system() != 'Windows':
                return RequirementResult(
                    requirement=requirement,
                    passed=False,
                    current_value=platform.system(),
                    message=f"Windows required, found: {platform.system()}"
                )
            
            version = platform.version()
            release = platform.release()
            
            # Parse Windows version
            version_parts = version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1])
            build = int(version_parts[2]) if len(version_parts) > 2 else 0
            
            # Windows 10 is version 10.0, Windows 11 is 10.0 with build >= 22000
            current_version = f"{major}.{minor}"
            
            # Determine if Windows 11
            is_win11 = major >= 10 and build >= 22000
            display_version = "11.0" if is_win11 else current_version
            
            passed = float(current_version) >= float(requirement.minimum_value)
            
            if is_win11:
                message = f"Excellent: Windows 11 (build {build})"
            elif passed:
                message = f"Compatible: Windows {release} ({current_version})"
            else:
                message = f"Incompatible: Windows {release} (minimum: Windows 10)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=display_version,
                message=message,
                details={"release": release, "build": build}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check Windows version: {e}"
            )
    
    def check_architecture(self, requirement: SystemRequirement) -> RequirementResult:
        """Check system architecture."""
        try:
            architecture = platform.architecture()[0]
            machine = platform.machine()
            
            passed = architecture == "64bit"
            
            if passed:
                message = f"Compatible: {architecture} architecture ({machine})"
            else:
                message = f"Incompatible: {architecture} architecture (64-bit required)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=architecture,
                message=message,
                details={"machine": machine}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check architecture: {e}"
            )
    
    def check_python_version(self, requirement: SystemRequirement) -> RequirementResult:
        """Check Python version (if available)."""
        try:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            passed = float(python_version) >= float(requirement.minimum_value)
            
            if float(python_version) >= float(requirement.recommended_value):
                message = f"Excellent: Python {python_version}"
            elif passed:
                message = f"Compatible: Python {python_version}"
            else:
                message = f"Outdated: Python {python_version} (minimum: {requirement.minimum_value})"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=python_version,
                message=message
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=True,  # Optional requirement
                current_value=None,
                message="Python not available (not required for executable)"
            )
    
    def check_internet_connectivity(self, requirement: SystemRequirement) -> RequirementResult:
        """Check internet connectivity."""
        try:
            # Test connectivity to multiple reliable hosts
            test_hosts = [
                ("google.com", 80),
                ("github.com", 443),
                ("ollama.ai", 443)
            ]
            
            connected_hosts = []
            for host, port in test_hosts:
                try:
                    socket.create_connection((host, port), timeout=5).close()
                    connected_hosts.append(host)
                except (socket.error, socket.timeout):
                    continue
            
            passed = len(connected_hosts) > 0
            
            if len(connected_hosts) == len(test_hosts):
                message = "Excellent: Full internet connectivity"
            elif passed:
                message = f"Partial connectivity: {len(connected_hosts)}/{len(test_hosts)} hosts reachable"
            else:
                message = "No internet connectivity detected"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=len(connected_hosts),
                message=message,
                details={"reachable_hosts": connected_hosts}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check connectivity: {e}"
            )
    
    def check_dns_resolution(self, requirement: SystemRequirement) -> RequirementResult:
        """Check DNS resolution."""
        try:
            test_domains = ["google.com", "github.com", "ollama.ai"]
            resolved_domains = []
            
            for domain in test_domains:
                try:
                    socket.gethostbyname(domain)
                    resolved_domains.append(domain)
                except socket.gaierror:
                    continue
            
            passed = len(resolved_domains) > 0
            
            if len(resolved_domains) == len(test_domains):
                message = "Excellent: DNS resolution working"
            elif passed:
                message = f"Partial DNS: {len(resolved_domains)}/{len(test_domains)} domains resolved"
            else:
                message = "DNS resolution not working"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=len(resolved_domains),
                message=message,
                details={"resolved_domains": resolved_domains}
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=False,
                current_value=None,
                message=f"Failed to check DNS: {e}"
            )
    
    def check_gpu_memory(self, requirement: SystemRequirement) -> RequirementResult:
        """Check GPU memory (optional for acceleration)."""
        try:
            # This is a simplified check - in practice would use nvidia-smi or similar
            # For now, just check if we can find any indication of GPU
            
            gpu_found = False
            gpu_memory = 0
            
            # Try to check NVIDIA GPU
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    gpu_memory = int(result.stdout.strip()) / 1024  # Convert MB to GB
                    gpu_found = True
            except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
                pass
            
            if gpu_found:
                passed = gpu_memory >= requirement.minimum_value
                if gpu_memory >= requirement.recommended_value:
                    message = f"Excellent: {gpu_memory:.1f} GB GPU memory"
                elif passed:
                    message = f"Good: {gpu_memory:.1f} GB GPU memory"
                else:
                    message = f"Limited: {gpu_memory:.1f} GB GPU memory (recommended: {requirement.minimum_value} GB)"
            else:
                passed = True  # Optional requirement
                message = "No dedicated GPU detected (CPU processing will be used)"
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=gpu_memory if gpu_found else None,
                message=message
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=True,  # Optional requirement
                current_value=None,
                message=f"Could not check GPU memory: {e}"
            )
    
    def check_windows_defender(self, requirement: SystemRequirement) -> RequirementResult:
        """Check Windows Defender status."""
        try:
            if platform.system() != 'Windows':
                return RequirementResult(
                    requirement=requirement,
                    passed=True,
                    current_value=None,
                    message="Not applicable (non-Windows system)"
                )
            
            # Try to check Windows Defender status
            try:
                result = subprocess.run([
                    'powershell', '-Command',
                    'Get-MpComputerStatus | Select-Object -Property RealTimeProtectionEnabled'
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0 and 'True' in result.stdout:
                    message = "Windows Defender real-time protection enabled"
                    passed = True
                elif result.returncode == 0 and 'False' in result.stdout:
                    message = "Windows Defender real-time protection disabled"
                    passed = True  # Still OK, just noting the status
                else:
                    message = "Could not determine Windows Defender status"
                    passed = True  # Assume OK
                    
            except subprocess.TimeoutExpired:
                message = "Windows Defender status check timed out"
                passed = True  # Assume OK
                
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=None,
                message=message
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=True,  # Non-critical
                current_value=None,
                message=f"Could not check Windows Defender: {e}"
            )
    
    def check_execution_policy(self, requirement: SystemRequirement) -> RequirementResult:
        """Check PowerShell execution policy."""
        try:
            if platform.system() != 'Windows':
                return RequirementResult(
                    requirement=requirement,
                    passed=True,
                    current_value=None,
                    message="Not applicable (non-Windows system)"
                )
            
            result = subprocess.run([
                'powershell', '-Command', 'Get-ExecutionPolicy'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                policy = result.stdout.strip()
                
                # Policies that allow script execution
                permissive_policies = ['Unrestricted', 'RemoteSigned', 'AllSigned', 'Bypass']
                passed = policy in permissive_policies
                
                if passed:
                    message = f"PowerShell execution policy: {policy}"
                else:
                    message = f"Restrictive PowerShell policy: {policy} (may limit functionality)"
                    
            else:
                message = "Could not determine PowerShell execution policy"
                passed = True  # Assume OK
            
            return RequirementResult(
                requirement=requirement,
                passed=passed,
                current_value=policy if result.returncode == 0 else None,
                message=message
            )
            
        except Exception as e:
            return RequirementResult(
                requirement=requirement,
                passed=True,  # Non-critical
                current_value=None,
                message=f"Could not check execution policy: {e}"
            )
    
    def run_all_checks(self) -> List[RequirementResult]:
        """Run all system requirement checks."""
        self.logger.info("Starting comprehensive system requirements check...")
        
        results = []
        
        for requirement in self.requirements:
            self.logger.debug(f"Checking: {requirement.name}")
            
            try:
                # Get the check function and call it
                check_method = getattr(self, requirement.check_function)
                result = check_method(requirement)
                results.append(result)
                
                # Log result
                status = "PASS" if result.passed else "FAIL"
                self.logger.info(f"{status}: {requirement.name} - {result.message}")
                
            except Exception as e:
                self.logger.error(f"Error checking {requirement.name}: {e}")
                results.append(RequirementResult(
                    requirement=requirement,
                    passed=False,
                    current_value=None,
                    message=f"Check failed: {e}"
                ))
        
        return results
    
    def generate_report(self, results: List[RequirementResult]) -> Dict:
        """Generate comprehensive requirements report."""
        report = {
            "system_info": {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "username": os.getlogin() if hasattr(os, 'getlogin') else "unknown"
            },
            "summary": {
                "total_checks": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
                "critical_failures": sum(1 for r in results 
                                       if not r.passed and r.requirement.level == RequirementLevel.CRITICAL)
            },
            "requirements": []
        }
        
        for result in results:
            report["requirements"].append({
                "name": result.requirement.name,
                "description": result.requirement.description,
                "level": result.requirement.level.value,
                "passed": result.passed,
                "current_value": result.current_value,
                "minimum_value": result.requirement.minimum_value,
                "recommended_value": result.requirement.recommended_value,
                "unit": result.requirement.unit,
                "message": result.message,
                "details": result.details
            })
        
        # Overall compatibility assessment
        critical_failures = report["summary"]["critical_failures"]
        if critical_failures == 0:
            report["compatibility"] = "COMPATIBLE"
            report["recommendation"] = "System meets all critical requirements for ComBadge"
        else:
            report["compatibility"] = "INCOMPATIBLE" 
            report["recommendation"] = f"System has {critical_failures} critical requirement failures"
        
        return report
    
    def save_report(self, report: Dict, output_file: Path):
        """Save requirements report to file."""
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Requirements report saved to: {output_file}")


def main():
    """Main entry point for system requirements checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check ComBadge system requirements")
    parser.add_argument("--output", "-o", help="Output report file (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--silent", "-s", action="store_true", help="Silent mode (only errors)")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.silent:
        logging.getLogger().setLevel(logging.ERROR)
    
    checker = SystemRequirementsChecker()
    results = checker.run_all_checks()
    report = checker.generate_report(results)
    
    # Print summary
    if not args.silent:
        print("\n" + "="*60)
        print("COMBADGE SYSTEM REQUIREMENTS REPORT")
        print("="*60)
        print(f"System: {report['system_info']['platform']}")
        print(f"Compatibility: {report['compatibility']}")
        print(f"Checks: {report['summary']['passed']}/{report['summary']['total_checks']} passed")
        
        if report['summary']['critical_failures'] > 0:
            print(f"⚠️  CRITICAL FAILURES: {report['summary']['critical_failures']}")
        
        print(f"\nRecommendation: {report['recommendation']}")
        print("="*60)
        
        # Show failed requirements
        failed_requirements = [r for r in results if not r.passed]
        if failed_requirements:
            print("\nFAILED REQUIREMENTS:")
            for result in failed_requirements:
                level_icon = "❌" if result.requirement.level == RequirementLevel.CRITICAL else "⚠️"
                print(f"{level_icon} {result.requirement.description}: {result.message}")
    
    # Save report if requested
    if args.output:
        checker.save_report(report, Path(args.output))
    
    # Exit with appropriate code
    if report['summary']['critical_failures'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()