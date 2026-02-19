"""
Object Data Model

Represents an object (person) in the Vigil surveillance system.
Based on original main.py implementation with validation and display methods.
"""

from typing import Dict, Any, Optional
from transliterate import translit


class Object:
    """Represents a recognized object/person in the system."""
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """Initialize object from data dictionary."""
        if data:
            self._from_dict(data)
        else:
            self._init_defaults()
    
    def _init_defaults(self) -> None:
        """Initialize with default values."""
        self.last_name = ""
        self.first_name = ""
        self.phone = ""
        self.category = "4"  # Default to unknown (red avatar)
        self.homenumb = "0"
        self.apartmentnumb = "0"
        self.floornumb = "0"
        self.modelfolder = ""
        self.foto = "no_avatar_red.jpg"
        self.userlink = ""
        self.ob_komments = ""
        self.ob_sets01 = ""
        self.ob_sets02 = ""
        self.ob_sets03 = ""
        self.ob_sets04 = ""
        self.ob_sets05 = ""
    
    def _from_dict(self, data: Dict[str, Any]) -> None:
        """Initialize from data dictionary."""
        self.last_name = data.get('last_name', "")
        self.first_name = data.get('first_name', "")
        self.phone = data.get('phone', "")
        self.category = data.get('category', "4")
        self.homenumb = data.get('homenumb', "0")
        self.apartmentnumb = data.get('apartmentnumb', "0")
        self.floornumb = data.get('floornumb', "0")
        self.modelfolder = data.get('modelfolder', "")
        self.foto = data.get('foto', "no_avatar_red.jpg")
        self.userlink = data.get('userlink', "")
        self.ob_komments = data.get('ob_komments', "")
        self.ob_sets01 = data.get('ob_sets01', "")
        self.ob_sets02 = data.get('ob_sets02', "")
        self.ob_sets03 = data.get('ob_sets03', "")
        self.ob_sets04 = data.get('ob_sets04', "")
        self.ob_sets05 = data.get('ob_sets05', "")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            'last_name': self.last_name,
            'first_name': self.first_name,
            'phone': self.phone,
            'category': self.category,
            'homenumb': self.homenumb,
            'apartmentnumb': self.apartmentnumb,
            'floornumb': self.floornumb,
            'modelfolder': self.modelfolder,
            'foto': self.foto,
            'userlink': self.userlink,
            'ob_komments': self.ob_komments,
            'ob_sets01': self.ob_sets01,
            'ob_sets02': self.ob_sets02,
            'ob_sets03': self.ob_sets03,
            'ob_sets04': self.ob_sets04,
            'ob_sets05': self.ob_sets05
        }
    
    def get_full_name(self) -> str:
        """Get full name (first + last)."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return "Unknown"
    
    def get_category_name(self) -> str:
        """Get category description."""
        categories = {
            '1': 'Resident',
            '2': 'Staff',
            '3': 'Visitor',
            '4': 'Unknown'
        }
        return categories.get(self.category, 'Unknown')
    
    def get_avatar_filename(self) -> str:
        """Get avatar filename based on category."""
        avatars = {
            '1': 'no_avatar_green.jpg',
            '2': 'no_avatar_grey.jpg',
            '3': 'no_avatar_blue.jpg',
            '4': 'no_avatar_red.jpg'
        }
        return avatars.get(self.category, 'no_avatar_red.jpg')
    
    def get_address(self) -> str:
        """Get formatted address string."""
        parts = []
        if self.homenumb and self.homenumb != "0":
            parts.append(f"House {self.homenumb}")
        if self.apartmentnumb and self.apartmentnumb != "0":
            parts.append(f"Apt {self.apartmentnumb}")
        if self.floornumb and self.floornumb != "0":
            parts.append(f"Floor {self.floornumb}")
        
        return ", ".join(parts) if parts else "No address"
    
    def generate_model_folder(self, number: int) -> str:
        """Generate model folder name with transliteration."""
        if not self.first_name:
            return f"{number}_{self.category}_Unknown"
        
        # Transliterate first name
        transliterated = ''.join(
            translit(char, "ru", "en") if 'а' <= char <= 'я' or 'А' <= char <= 'Я' else char
            for char in self.first_name.strip()
        )
        
        return f"{number}_{self.category}_{transliterated}"
    
    def validate(self) -> tuple[bool, str]:
        """Validate object data."""
        errors = []
        
        # Validate first name
        if not self.first_name:
            errors.append("First name is required")
        elif len(self.first_name) > 20:
            errors.append("First name too long (max 20 characters)")
        elif not self._validate_name_format(self.first_name):
            errors.append("First name contains invalid characters")
        
        # Validate last name
        if not self.last_name:
            errors.append("Last name is required")
        elif len(self.last_name) > 20:
            errors.append("Last name too long (max 20 characters)")
        elif not self._validate_name_format(self.last_name):
            errors.append("Last name contains invalid characters")
        
        # Validate comments
        if self.ob_komments and len(self.ob_komments) > 500:
            errors.append("Comments too long (max 500 characters)")
        
        return len(errors) == 0, "; ".join(errors)
    
    def _validate_name_format(self, name: str) -> bool:
        """Validate name format (Russian/English letters only)."""
        if not name:
            return False
        import re
        return bool(re.match(r'^[а-яА-ЯёЁa-zA-Z0-9]+$', name.strip()))
    
    def is_editable(self) -> bool:
        """Check if object can be edited (not Unknown)."""
        return self.modelfolder != "Unknown"
    
    def is_deletable(self) -> bool:
        """Check if object can be deleted (not Unknown)."""
        return self.modelfolder != "Unknown"
    
    def __str__(self) -> str:
        """String representation."""
        return self.get_full_name()
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Object(name='{self.get_full_name()}', category='{self.get_category_name()}', folder='{self.modelfolder}')"
