from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
import adsk, adsk.core, adsk.fusion, traceback
import numpy as np
from .urdf_utils import get_occurrence_tf, tf_to_rpy_str, tf_to_xyz_str

class Joint(Element):
    def __init__(self, name: str, joint: adsk.fusion.AsBuiltJoint, cmd_inputs: adsk.core.CommandInputs, app: adsk.core.Application):
        if name == 'base':
            joint_type = 'fixed'
        else:
            joint_type = self.convert_fusion_joint_type_to_URDF(joint=joint)
        super().__init__("joint", attrib={"name": f"{name}_joint", "type": joint_type})
        self._cmd_inputs = cmd_inputs
        self._app = app
        self.__origin = Element("origin", attrib={"xyz": "0 0 0", "rpy": "0 0 0"})
        self.__parent = Element("parent", attrib={"link": ""})
        self.__child = Element("child", attrib={"link": ""})
        self.append(self.__origin)
        self.append(self.__parent)
        self.append(self.__child)
        self.set_joint_dynamics(joint=joint)
        if(joint_type != 'fixed'):
            self.set_axis_value(joint=joint)
            self.set_joint_limits(joint=joint)

    def convert_fusion_joint_type_to_URDF(self, joint: adsk.fusion.AsBuiltJoint) -> str:
        joint_type = joint.jointMotion.jointType
        if(joint_type == adsk.fusion.JointTypes.RevoluteJointType):
            joint_motion = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
            if(joint_motion.rotationLimits.isMaximumValueEnabled == True) and (joint_motion.rotationLimits.isMinimumValueEnabled == True):
                return 'revolute'
            else:
                return 'continuous'
        else:
            return 'fixed'
        
    def set_joint_limits(self, joint: adsk.fusion.AsBuiltJoint):
        if(joint.jointMotion.jointType == adsk.fusion.JointTypes.RevoluteJointType):
            joint_motion = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
            if(joint_motion.rotationLimits.isMaximumValueEnabled == True) and (joint_motion.rotationLimits.isMinimumValueEnabled == True):
                self.__limit = Element("limit", attrib={"lower": f'{round(joint_motion.rotationLimits.minimumValue, 6)}',
                                                        "upper": f'{round(joint_motion.rotationLimits.maximumValue, 6)}',
                                                        "effort": '1000.0',
                                                        "velocity": '100.0',})
                self.append(self.__limit)

    def set_joint_dynamics(self, joint: adsk.fusion.AsBuiltJoint):
        joint_dynamics_table = adsk.core.TableCommandInput.cast(self._cmd_inputs.itemById('joint_dynamics_table'))
        self.__dynamics = Element("dynamics")
        for i in range(1, joint_dynamics_table.rowCount):
            if joint.name.replace(" ", "_") == joint_dynamics_table.getInputAtPosition(i, 0).value:
                joint_friction = float(joint_dynamics_table.getInputAtPosition(i, 1).value)
                joint_damping = float(joint_dynamics_table.getInputAtPosition(i, 2).value)
                if joint_friction != 0.0 and joint_damping != 0.0:
                    self.__dynamics.attrib['friction'] = str(joint_friction)
                    self.__dynamics.attrib['damping'] = str(joint_damping)
                    self.append(self.__dynamics)
        
    def set_axis_value(self, joint: adsk.fusion.AsBuiltJoint):
        axis_vector = joint.geometry.primaryAxisVector.asArray()
        self.__axis = Element("axis", attrib={"xyz": f"{round(axis_vector[0], 6)} {round(axis_vector[1], 6)} {round(axis_vector[2], 6)}"})
        self.append(self.__axis)

    def get_parent_value(self):
        return self.__parent.attrib["link"]

    def get_child_value(self):
        return self.__child.attrib["link"]

    def get_xyz_value(self):
        return self.__origin.attrib["xyz"]

    def get_rpy_value(self):
        return self.__origin.attrib["rpy"]

    def set_parent_value(self, parent_link: str, override_suffix: bool = False):
        if override_suffix:
            self.__parent.attrib["link"] = f'{parent_link}'
        else:
            self.__parent.attrib["link"] = f'{parent_link}_link'

    def set_child_value(self, child_link: str, override_suffix: bool = False):
        if override_suffix:
            self.__child.attrib["link"] = f'{child_link}'
        else:
            self.__child.attrib["link"] = f'{child_link}_link'

    def set_xyz_value(self, xyz):
        if type(xyz) == list:
            xyz = f"{round(xyz[0] /100, 6)} {round(xyz[1] /100, 6)} {round(xyz[2] /100, 6)}"
        self.__origin.attrib["xyz"] = xyz

    def set_rpy_value(self, rpy):
        if type(rpy) == list:
            rpy = f"{round(rpy[0], 6)} {round(rpy[1], 6)} {round(rpy[2], 6)}"
        self.__origin.attrib["rpy"] = rpy

    def set_from_tf(self, tf: np.ndarray[(4,4), np.dtype[any]]):
        self.set_xyz_value(xyz=tf_to_xyz_str(tf=tf))
        self.set_rpy_value(rpy=tf_to_rpy_str(tf=tf))