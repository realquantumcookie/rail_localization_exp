import typing
import numpy as np
import time


class NonBlocking:
    def update(self) -> None:
        return


"""
Note: The ordering of location/velocity/acceleration is: [x, y, z, degX, degY, degZ]
Or in other words: [x, y, z, roll, pitch, yaw]
autoUpdate decides if any other variables should be used to update the current variable
"""

"""
Returns angX, angY, angZ
"""
def rotation_angle(rot_matrix : np.ndarray) -> typing.Tuple[float, float, float]:
    assert rot_matrix.shape == (3,3)
    return (
        np.arctan2(rot_matrix[2,1], rot_matrix[2,2]), 
        np.arctan2(-rot_matrix[2,0], np.sqrt(rot_matrix[2,1]**2 + rot_matrix[2,2]**2)), 
        np.arctan2(rot_matrix[1,0], rot_matrix[0,0])
    )

# gives WXYZ quaternion
# https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
def quaternion_from_rotation(roll, pitch, yaw) -> typing.Tuple[float,float,float,float]:
    # Abbreviations for the various angular functions
    cy = np.cos(yaw * 0.5);
    sy = np.sin(yaw * 0.5);
    cp = np.cos(pitch * 0.5);
    sp = np.sin(pitch * 0.5);
    cr = np.cos(roll * 0.5);
    sr = np.sin(roll * 0.5);

    w = cr * cp * cy + sr * sp * sy;
    x = sr * cp * cy - cr * sp * sy;
    y = cr * sp * cy + sr * cp * sy;
    z = cr * cp * sy - sr * sp * cy;

    return (w,x,y,z);

# https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
def rotation_angle_from_quaternion(q) -> typing.Tuple[float,float,float]:
    
    # roll (x-axis rotation)
    sinr_cosp = 2 * (q[0] * q[1] + q[2] * q[3])
    cosr_cosp = 1 - 2 * (q[1] * q[1] + q[2] * q[2])
    
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # pitch (y-axis rotation)
    sinp = 2 * (q[0] * q[2] - q[3] * q[1])
    pitch = 0
    if (np.abs(sinp) >= 1):
        pitch = np.copysign(np.pi / 2, sinp) # use 90 degrees if out of range
    else:
        pitch = np.arcsin(sinp)

    # yaw (z-axis rotation)
    siny_cosp = 2 * (q[0] * q[3] + q[1] * q[2])
    cosy_cosp = 1 - 2 * (q[2] * q[2] + q[3] * q[3])
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)

def rotation_matrix(
    roll,
    pitch,
    yaw
) -> np.ndarray:
    c1 = np.cos(roll)
    c2 = np.cos(pitch)
    c3 = np.cos(yaw)
    s1 = np.sin(roll)
    s2 = np.sin(pitch)
    s3 = np.sin(yaw)

    R_Z = np.array([
        [c3, -s3, 0],
        [s3 , c3, 0],
        [0, 0, 1]
    ])

    R_Y = np.array([
        [c2, 0, s2],
        [0 ,1 ,0],
        [-s2, 0, c2]
    ])

    R_X = np.array([
        [1, 0, 0],
        [0, c1, -s1],
        [0, s1, c1]
    ])
    
    return (R_Z @ R_Y @ R_X)

    """
    return np.array([
        [c1*c2, c1*s2*s3 - c3*s1, s1*s3 + c1*c3*s2],
        [c2*s1, c1*c3 + s1*s2*s3, c3*s1*s2 - c1*s3],
        [s2, c2*s3, c2*c3]
    ])
    """

def rotation_matrix_inverse(
    roll,
    pitch,
    yaw
) -> np.ndarray:
    #return np.linalg.inv(rotation_matrix(roll, pitch, yaw))
    c1 = np.cos(-roll)
    c2 = np.cos(-pitch)
    c3 = np.cos(-yaw)
    s1 = np.sin(-roll)
    s2 = np.sin(-pitch)
    s3 = np.sin(-yaw)

    R_Z = np.array([
        [c3, -s3, 0],
        [s3 , c3, 0],
        [0, 0, 1]
    ])

    R_Y = np.array([
        [c2, 0, s2],
        [0 ,1 ,0],
        [-s2, 0, c2]
    ])

    R_X = np.array([
        [1, 0, 0],
        [0, c1, -s1],
        [0, s1, c1]
    ])
    
    return (R_X @ R_Y @ R_Z)

def coordinate_transform_to_global(
    to_transform: np.ndarray,
    robot_global_location: np.ndarray
) -> np.ndarray:
    assert to_transform.shape == (6,) and robot_global_location.shape == (6,)

    int_mat = np.hstack([
        to_transform[:3],
        wrap_angle_rad(to_transform[3:])
    ]).reshape(3,2)
    rot_mat = rotation_matrix(*robot_global_location[3:])
    int_rst = rot_mat @ int_mat
    return np.vstack([
        int_rst[:,0] + robot_global_location[:3],
        wrap_angle_rad(int_rst[:,1])
    ]).reshape(6,)

def coordinate_transform_to_local(
    to_transform: np.ndarray,
    robot_global_location: np.ndarray
) -> np.ndarray:
    assert to_transform.shape == (6,) and robot_global_location.shape == (6,)
    
    int_mat = np.hstack([
        to_transform[:3] - robot_global_location[:3],
        wrap_angle_rad(to_transform[3:])
    ]).reshape(3,2)
    rot_mat = rotation_matrix_inverse(*robot_global_location[3:])
    int_rst = rot_mat @ int_mat
    return np.vstack([
        int_rst[:,0],
        wrap_angle_rad(int_rst[:,1])
    ]).reshape(6,)

def wrap_angle_rad(angle: float) -> float: # Wrap angle to [-pi, pi]
    return angle % (2 * np.pi)


class LocalFrameEstimator:
    def subscribeLocalVelocity(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        raise NotImplementedError
    
    def subscribeLocalAcceleration(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        raise NotImplementedError

    def unsubscribeLocalVelocity(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        raise NotImplementedError
    
    def unsubscribeLocalAcceleration(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        raise NotImplementedError
    
    def getLocalVelocity(self) -> typing.Optional[np.ndarray]:
        raise NotImplementedError
    
    def getLocalAcceleration(self) -> typing.Optional[np.ndarray]:
        raise NotImplementedError

class LocalFrameEstimatorImpl(LocalFrameEstimator):
    def __init__(self, name: str, autoUpdateVelocity : bool = True, autoUpdateAcceleration : bool = True):
        self.name = name
        self.autoUpdateVelocity = autoUpdateVelocity
        self.autoUpdateAcceleration = autoUpdateAcceleration

        self.__localVelocitySubscribeList : typing.List[typing.Callable[[LocalFrameEstimator, np.ndarray], None]] = []
        self.__localAccelerationSubscribeList : typing.List[typing.Callable[[LocalFrameEstimator, np.ndarray], None]] = []

        self.__lastLocalVelocity : np.ndarray = np.zeros(6)
        self.__lastLocalVelocityUpdate : float = 0
        self.__lastLocalAcceleration : np.ndarray = np.zeros(6)
        self.__lastLocalAccelerationUpdate : float = 0
    
    def __str__(self) -> str:
        return self.name + "(LocalFrameEstimatorImpl)"

    def subscribeLocalVelocity(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self.__localVelocitySubscribeList.append(callback)
    
    def subscribeLocalAcceleration(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self.__localAccelerationSubscribeList.append(callback)
    
    def unsubscribeLocalVelocity(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self.__localVelocitySubscribeList.remove(callback)
    
    def unsubscribeLocalAcceleration(self, callback : typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self.__localAccelerationSubscribeList.remove(callback)

    def _call_local_velocity_update(self, new_local_velocity : np.ndarray) -> None:
        assert new_local_velocity.shape == (6,)
        
        ctime = time.time()
        if self.__lastLocalVelocityUpdate != 0:
            dt = ctime - self.__lastLocalVelocityUpdate
            self.__local_velocity_updated(new_local_velocity, self.__lastLocalVelocity, ctime, dt, True)
        else:
            self.__local_velocity_updated(new_local_velocity, None, ctime, None, False)
        
    def _call_local_acceleration_update(self, new_local_acceleration : np.ndarray) -> None:
        assert new_local_acceleration.shape == (6,)
        
        ctime = time.time()
        if self.__lastLocalAccelerationUpdate != 0:
            dt = ctime - self.__lastLocalAccelerationUpdate
            self.__local_acceleration_updated(new_local_acceleration, self.__lastLocalAcceleration, ctime, dt, True)
        else:
            self.__local_acceleration_updated(new_local_acceleration, None, ctime, None, True)
    
    def __local_velocity_updated(self, new_local_velocity : np.ndarray, old_local_velocity : typing.Optional[np.ndarray], ctime : float, dt : float, try_update_local_acceleration : bool = True) -> None:
        self.__lastLocalVelocity = new_local_velocity
        self.__lastLocalVelocityUpdate = ctime

        if try_update_local_acceleration and self.autoUpdateAcceleration and (old_local_velocity is not None):
            acceleration = (new_local_velocity - old_local_velocity) / dt
            self.__local_acceleration_updated(
                acceleration, 
                self.__lastLocalAcceleration, 
                ctime, 
                (ctime - self.__lastLocalAccelerationUpdate) if self.__lastLocalAccelerationUpdate != 0 else None, 
                False
            )
        
        for callback in self.__localVelocitySubscribeList:
            callback(self, new_local_velocity)

    
    def __local_acceleration_updated(self, new_local_acceleration : np.ndarray, old_local_acceleration : typing.Optional[np.ndarray], ctime : float, dt : float, try_update_local_velocity : bool = True) -> None:
        self.__lastLocalAcceleration = new_local_acceleration
        self.__lastLocalAccelerationUpdate = ctime

        if try_update_local_velocity and self.autoUpdateVelocity and self.__lastLocalVelocityUpdate != 0:
            velocity = np.zeros((6,))
            if old_local_acceleration is not None:
                velocity = self.__lastLocalVelocity + (new_local_acceleration + old_local_acceleration) / 2.0 * dt
            else:
                velocity = self.__lastLocalVelocity + new_local_acceleration * dt
            self.__local_velocity_updated(velocity, self.__lastLocalVelocity, ctime, ctime - self.__lastLocalVelocityUpdate, False)

        for callback in self.__localAccelerationSubscribeList:
            callback(self, new_local_acceleration)
        
    def getLocalVelocity(self) -> typing.Optional[np.ndarray]:
        return self.__lastLocalVelocity if self.__lastLocalVelocityUpdate != 0 else None
    
    def getLocalAcceleration(self) -> typing.Optional[np.ndarray]:
        return self.__lastLocalAcceleration if self.__lastLocalAccelerationUpdate != 0 else None


class GlobalFrameEstimator:
    def subscribe_location(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        raise NotImplementedError
    
    def unsubscribe_location(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        raise NotImplementedError
    
    def subscribe_velocity(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        raise NotImplementedError
    
    def unsubscribe_velocity(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        raise NotImplementedError

    def subscribe_acceleration(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        raise NotImplementedError
    
    def unsubscribe_acceleration(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        raise NotImplementedError
    
    def getLocation(self) -> typing.Optional[np.ndarray]:
        raise NotImplementedError
    
    def getVelocity(self) -> typing.Optional[np.ndarray]:
        raise NotImplementedError
    
    def getAcceleration(self) -> typing.Optional[np.ndarray]:
        raise NotImplementedError

class GlobalFrameEstimatorImpl(LocalFrameEstimator):
    def __init__(self, name : str, autoUpdateLocation : bool = True, autoUpdateVelocity : bool = True, autoUpdateAcceleration : bool = True, autoUpdateLocalVelocity : bool = True, autoUpdateLocalAcceleration : bool = True):
        self.name = name
        self._locationSubscribeList : typing.List[typing.Callable[[GlobalFrameEstimator,np.ndarray],None]] = []
        self._velocitySubscribeList : typing.List[typing.Callable[[GlobalFrameEstimator,np.ndarray],None]] = []
        self._accelerationSubscribeList : typing.List[typing.Callable[[GlobalFrameEstimator,np.ndarray],None]] = []
        self._localVelocitySubscribeList : typing.List[typing.Callable[[LocalFrameEstimator,np.ndarray],None]] = []
        self._localAccelerationSubscribeList : typing.List[typing.Callable[[LocalFrameEstimator,np.ndarray],None]] = []
        
        self.autoUpdateLocation = autoUpdateLocation
        self.autoUpdateVelocity = autoUpdateVelocity
        self.autoUpdateAcceleration = autoUpdateAcceleration
        self.autoupdateLocalVelocity = autoUpdateLocalVelocity
        self.autoUpdateLocalAcceleration = autoUpdateLocalAcceleration

        self.__lastLocationUpdate : float = 0
        self.__lastVelocityUpdate : float = 0
        self.__lastAccelerationUpdate : float = 0
        self.__lastAcceleration : np.ndarray = np.zeros(6)
        self.__lastVelocity : np.ndarray = np.zeros(6)
        self.__lastLocation : np.ndarray = np.zeros(6)
        self._lastLocalVelocity : typing.Optional[np.ndarray] = None
        self._lastLocalAcceleration : typing.Optional[np.ndarray] = None

    def __str__(self) -> str:
        return self.name + "(GlobalFrameEstimatorImpl)"
    
    def subscribe_location(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        self._locationSubscribeList.append(callback)
    
    def unsubscribe_location(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        self._locationSubscribeList.remove(callback)
    
    def subscribe_velocity(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        self._velocitySubscribeList.append(callback)
    
    def unsubscribe_velocity(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        self._velocitySubscribeList.remove(callback)

    def subscribe_acceleration(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        self._accelerationSubscribeList.append(callback)
    
    def unsubscribe_acceleration(self, callback : typing.Callable[[typing.Any,np.ndarray],None]):
        self._accelerationSubscribeList.remove(callback)
    
    def subscribeLocalVelocity(self, callback: typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self._localVelocitySubscribeList.append(callback)
    
    def unsubscribeLocalVelocity(self, callback: typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self._localVelocitySubscribeList.remove(callback)

    def subscribeLocalAcceleration(self, callback: typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self._localAccelerationSubscribeList.append(callback)
    
    def unsubscribeLocalAcceleration(self, callback: typing.Callable[[typing.Any, np.ndarray], None]) -> None:
        self._localAccelerationSubscribeList.remove(callback)

    def _call_location_update(self, new_location : np.ndarray) -> None:
        assert new_location.shape == (6,)
        
        ctime = time.time()
        if self.__lastLocationUpdate != 0:
            dt = ctime - self.__lastLocationUpdate
            self.__location_updated(new_location, self.__lastLocation, ctime, dt, True, True)
        else:
            self.__location_updated(new_location, None, ctime, None, False, False)
        
    def _call_velocity_update(self, new_velocity : np.ndarray) -> None:
        assert new_velocity.shape == (6,)
        
        ctime = time.time()
        if self.__lastVelocityUpdate != 0:
            dt = ctime - self.__lastVelocityUpdate
            self.__velocity_updated(new_velocity, self.__lastVelocity, ctime, dt, True, True)
        else:
            self.__velocity_updated(new_velocity, None, ctime, None, False, False)
    
    def _call_acceleration_update(self, new_acceleration : np.ndarray) -> None:
        assert new_acceleration.shape == (6,)
        
        ctime = time.time()
        if self.__lastAccelerationUpdate != 0:
            dt = ctime - self.__lastAccelerationUpdate
            self.__acceleration_updated(new_acceleration, self.__lastAcceleration, ctime, dt, True, True)
        else:
            self.__acceleration_updated(new_acceleration, None, ctime, None, False, False)
    
    def __location_updated(self,new_location : np.ndarray, old_location : typing.Optional[np.ndarray], time : float, dt : typing.Optional[float], try_update_velocity: bool = True, try_update_acceleration : bool = True) -> None:
        self.__lastLocation = new_location
        self.__lastLocationUpdate = time
        
        if try_update_velocity and (old_location is not None) and self.autoUpdateVelocity:
            velocity = (new_location - old_location) / dt
            self.__velocity_updated(
                velocity, 
                self.__lastVelocity, 
                time, 
                (time - self.__lastVelocityUpdate) if self.__lastVelocityUpdate != 0 else None, 
                try_update_location = False, 
                try_update_acceleration = try_update_acceleration
            )
        
        for callback in self._locationSubscribeList:
            callback(self,new_location)
    
    def __velocity_updated(self,new_velocity : np.ndarray, old_velocity : typing.Optional[np.ndarray], time : float, dt : typing.Optional[float], try_update_location : bool = True, try_update_acceleration : bool = True) -> None:
        self.__lastVelocity = new_velocity
        self.__lastVelocityUpdate = time

        if try_update_acceleration and (old_velocity is not None) and self.autoUpdateAcceleration:
            acceleration = (new_velocity - old_velocity) / dt
            self.__acceleration_updated(
                acceleration, 
                self.__lastAcceleration, 
                time, 
                (time - self.__lastAccelerationUpdate) if self.__lastAccelerationUpdate != 0 else None, 
                try_update_location = False, 
                try_update_velocity = False
            )
        
        if try_update_location and self.autoUpdateLocation and self.__lastLocationUpdate != 0:
            location = np.zeros((6,))
            if old_velocity is not None:
                location = self.__lastLocation + (new_velocity + old_velocity) / 2.0 * dt
            else:
                location = self.__lastLocation + new_velocity * dt

            self.__location_updated(
                location, 
                self.__lastLocation, 
                time, 
                (time - self.__lastLocationUpdate) if self.__lastLocationUpdate != 0  else None, 
                try_update_velocity = False, 
                try_update_acceleration = False
            )
        
        for callback in self._velocitySubscribeList:
            callback(self,new_velocity)
        
        if self.__lastLocationUpdate != 0 and self.autoupdateLocalVelocity:
            self._lastLocalVelocity = coordinate_transform_to_local(new_velocity, self.__lastLocation)
            for callback in self._localVelocitySubscribeList:
                callback(self,self._lastLocalVelocity)


    def __acceleration_updated(self,new_acceleration : np.ndarray, old_acceleration : typing.Optional[np.ndarray], time : float, dt : typing.Optional[float], try_update_location : bool = True, try_update_velocity : bool = True) -> None:
        self.__lastAcceleration = new_acceleration
        self.__lastAccelerationUpdate = time
        

        if try_update_velocity and self.autoUpdateVelocity and self.__lastVelocityUpdate != 0:
            velocity = np.zeros((6,))
            if old_acceleration is not None:
                velocity = self.__lastVelocity + (new_acceleration + old_acceleration) / 2.0 * dt
            else:
                velocity = self.__lastVelocity + new_acceleration * dt
            
            self.__velocity_updated(
                velocity, 
                self.__lastVelocity, 
                time, 
                (time - self.__lastVelocityUpdate) if self.__lastVelocityUpdate != 0 else None, 
                try_update_location = try_update_location, 
                try_update_acceleration = False
            )
        
        for callback in self._accelerationSubscribeList:
            callback(self,new_acceleration)

        if self.__lastLocationUpdate != 0 and self.autoUpdateLocalAcceleration:
            self._lastLocalAcceleration = coordinate_transform_to_local(new_acceleration, self.__lastLocation)
            for callback in self._localAccelerationSubscribeList:
                callback(self,self._lastLocalAcceleration)
        
    def getLocation(self) -> typing.Optional[np.ndarray]:
        return self.__lastLocation if self.__lastLocationUpdate != 0 else None

    def getVelocity(self) -> typing.Optional[np.ndarray]:
        return self.__lastVelocity if self.__lastVelocityUpdate != 0 else None
    
    def getAcceleration(self) -> typing.Optional[np.ndarray]:
        return self.__lastAcceleration if self.__lastAccelerationUpdate != 0 else None
    
    def getLocalVelocity(self) -> typing.Optional[np.ndarray]:
        return self._lastLocalVelocity
    
    def getLocalAcceleration(self) -> typing.Optional[np.ndarray]:
        return self._lastLocalAcceleration

class LocalCoordinateTransformedEstimatorImpl(LocalFrameEstimator):

    @classmethod
    def generateTransformMatrices(newX : np.ndarray, newY : np.ndarray, newZ : np.ndarray) -> typing.Tuple[np.ndarray, np.ndarray]:
        assert newX.shape == (3,) and newY.shape == (3,) and newZ.shape == (3,)
        
        newX_unit = newX / np.linalg.norm(newX)
        newY_unit = newY / np.linalg.norm(newY)
        newZ_unit = newZ / np.linalg.norm(newZ)

        toOriginalFrameMatrix = np.hstack([
            newX.reshape((3,1)),
            newY.reshape((3,1)),
            newZ.reshape((3,1))
        ])

        toNewFrameMatrix = np.linalg.inv(toOriginalFrameMatrix)

        toOriginalFrameMatrixUnit = np.hstack([
            newX_unit.reshape((3,1)),
            newY_unit.reshape((3,1)),
            newZ_unit.reshape((3,1))
        ])

        toNewFrameMatrixUnit = np.linalg.inv(toOriginalFrameMatrixUnit)

        return toOriginalFrameMatrix, toNewFrameMatrix, toOriginalFrameMatrixUnit, toNewFrameMatrixUnit


    def __init__(
        self, 
        base : LocalFrameEstimator, 
        newX : np.ndarray,
        newY : np.ndarray,
        newZ : np.ndarray
    ):
        assert newX.shape == (3,) and newY.shape == (3,) and newZ.shape == (3,)
        self.__newX = newX
        self.__newY = newY
        self.__newZ = newZ

        self.__calcNewTransformMat()
    
    def __calcNewTransformMat(self):
        (self.__toOriginalFrameMat, self.__toNewFrameMat, self.__toOriginalFrameMatUnit, self.__toNewFrameMatUnit) : typing.Tuple[np.ndarray,np.ndarray, np.ndarray,np.ndarray] = __class__.generateTransformMatrices(self.__newX, self.__newY, self.__newZ)
    

    def getNewX(self):
        return self.__newX
    
    def getNewY(self):
        return self.__newY
    
    def getNewZ(self):
        return self.__newZ
    
    def setNewX(self, newX: np.ndarray):
        assert newX.shape == (3,)

        self.__newX = newX
        self.__calcNewTransformMat()

    def setNewY(self, newY: np.ndarray):
        assert newY.shape == (3,)

        self.__newY = newY
        self.__calcNewTransformMat()

    def setNewZ(self, newZ: np.ndarray):
        assert newZ.shape == (3,)

        self.__newZ = newZ
        self.__calcNewTransformMat()

    def getLocalAcceleration(self) -> typing.Optional[np.ndarray]:
        superAcc = super().getLocalAcceleration()
        if superAcc is None:
            return None
        else:
            return np.concatenate(
                self.__toNewFrameMat @ superAcc[:3].reshape((3,1)),
                self.__toNewFrameMatUnit @ superAcc[3:].reshape((3,1))
            ).reshape((6,))
    
    def getLocalVelocity(self) -> typing.Optional[np.ndarray]:
        superVel = super().getLocalVelocity()
        if superVel is None:
            return None
        else:
            return np.concatenate(
                self.__toNewFrameMat @ superVel[:3].reshape((3,1)),
                self.__toNewFrameMatUnit @ superVel[3:].reshape((3,1))
            ).reshape((6,))