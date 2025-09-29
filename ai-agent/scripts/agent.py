#!/usr/bin/env python3
"""
AI Agentic Pull Request System - Core Agent Implementation

This module provides the core functionality for the AI-driven pull request automation system.
"""

import os
import sys
import yaml
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import subprocess


@dataclass
class AgentConfig:
    """Configuration for the AI Agent"""
    name: str
    version: str
    description: str
    github_api_url: str
    github_token: Optional[str]
    ai_model_provider: str
    ai_model_name: str
    auto_create_pr: bool
    security_scan: bool


class AIAgent:
    """Core AI Agent for pull request automation"""
    
    def __init__(self, config_path: str):
        """Initialize the AI Agent with configuration"""
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
    def _load_config(self) -> AgentConfig:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            return AgentConfig(
                name=config_data['agent']['name'],
                version=config_data['agent']['version'],
                description=config_data['agent']['description'],
                github_api_url=config_data['github']['api_url'],
                github_token=os.environ.get(config_data['github']['token_env_var']),
                ai_model_provider=config_data['ai_model']['provider'],
                ai_model_name=config_data['ai_model']['model'],
                auto_create_pr=config_data['pull_request']['auto_create'],
                security_scan=config_data['security']['scan_for_secrets']
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('ai_agent')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(self.config_path), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(os.path.join(log_dir, 'agent.log'))
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def analyze_repository(self) -> Dict[str, Any]:
        """Analyze the current repository for improvement opportunities"""
        self.logger.info("🔍 Analyzing repository...")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'repository_path': os.getcwd(),
            'findings': [],
            'recommendations': []
        }
        
        # Check for common issues
        findings = []
        
        # Check for large files
        try:
            result = subprocess.run(['find', '.', '-type', 'f', '-size', '+10M'], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                findings.append({
                    'type': 'large_files',
                    'description': 'Large files detected that might need .gitignore',
                    'files': result.stdout.strip().split('\n')
                })
        except Exception as e:
            self.logger.warning(f"Could not check for large files: {e}")
        
        # Check for potential security issues
        if self.config.security_scan:
            findings.extend(self._security_scan())
        
        analysis['findings'] = findings
        analysis['recommendations'] = self._generate_recommendations(findings)
        
        self.logger.info(f"Analysis completed. Found {len(findings)} issues.")
        return analysis
    
    def _security_scan(self) -> List[Dict[str, Any]]:
        """Perform basic security scanning"""
        self.logger.info("🔒 Performing security scan...")
        security_findings = []
        
        # Check for potential API keys or secrets in files
        try:
            # Look for common secret patterns
            patterns = [
                'api[_-]?key',
                'secret[_-]?key', 
                'password',
                'token',
                'credential'
            ]
            
            for pattern in patterns:
                result = subprocess.run(['grep', '-r', '-i', pattern, '.'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    # Filter out false positives
                    lines = result.stdout.strip().split('\n')
                    suspicious_lines = [line for line in lines 
                                      if not any(exclude in line.lower() 
                                               for exclude in ['.git/', 'test', 'example', 'config.yaml'])]
                    
                    if suspicious_lines:
                        security_findings.append({
                            'type': 'potential_secret',
                            'pattern': pattern,
                            'description': f'Potential secret pattern "{pattern}" found',
                            'matches': suspicious_lines[:5]  # Limit to first 5 matches
                        })
        except Exception as e:
            self.logger.warning(f"Security scan failed: {e}")
        
        return security_findings
    
    def _generate_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        for finding in findings:
            if finding['type'] == 'large_files':
                recommendations.append("Consider adding large files to .gitignore or using Git LFS")
            elif finding['type'] == 'potential_secret':
                recommendations.append("Review and remove any exposed secrets, use environment variables instead")
        
        if not findings:
            recommendations.append("Repository looks good! Consider adding automated testing if not present.")
        
        return recommendations
    
    def generate_pull_request(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate a pull request based on analysis"""
        self.logger.info("📝 Generating pull request content...")
        
        # Load PR template
        template_path = os.path.join(os.path.dirname(self.config_path), '..', 'templates', 'default-pr.md')
        
        try:
            with open(template_path, 'r') as f:
                template = f.read()
        except Exception as e:
            self.logger.warning(f"Could not load template: {e}")
            template = "## AI-Generated Pull Request\n\n{{ summary }}\n\n### Changes\n{{ changes }}"
        
        # Generate content based on analysis
        summary = f"AI Agent analyzed the repository and found {len(analysis['findings'])} areas for improvement"
        
        changes = "The following improvements are recommended:\n"
        for i, rec in enumerate(analysis['recommendations'], 1):
            changes += f"{i}. {rec}\n"
        
        impact = "This analysis helps identify potential improvements for code quality and security."
        notes = f"Analysis performed at {analysis['timestamp']} by {self.config.name} v{self.config.version}"
        
        # Simple template substitution
        pr_content = template.replace('{{ agent.version }}', self.config.version)
        pr_content = pr_content.replace('{{ timestamp }}', analysis['timestamp'])
        pr_content = pr_content.replace('{{ trigger }}', 'automated_analysis')
        pr_content = pr_content.replace('{{ summary }}', summary)
        pr_content = pr_content.replace('{{ changes }}', changes)
        pr_content = pr_content.replace('{{ impact }}', impact)
        pr_content = pr_content.replace('{{ notes }}', notes)
        
        return {
            'title': f'AI Agent Analysis - {datetime.now().strftime("%Y-%m-%d")}',
            'body': pr_content,
            'branch': f'ai-agent/analysis-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        }
    
    def run(self) -> Dict[str, Any]:
        """Run the complete AI agent workflow"""
        self.logger.info(f"🤖 Starting {self.config.name} v{self.config.version}")
        
        try:
            # Analyze repository
            analysis = self.analyze_repository()
            
            # Generate PR content
            pr_data = self.generate_pull_request(analysis)
            
            # Log results
            self.logger.info("✅ AI Agent workflow completed successfully")
            
            return {
                'status': 'success',
                'analysis': analysis,
                'pull_request': pr_data
            }
            
        except Exception as e:
            self.logger.error(f"❌ AI Agent workflow failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python agent.py <config_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    
    agent = AIAgent(config_path)
    result = agent.run()
    
    # Output results
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()