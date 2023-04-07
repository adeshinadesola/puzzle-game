from enum import Enum
import math

class AnimationLerpFunction(Enum):
  linear = 'linear'
  ease_out = 'ease_out'
  ease_in = 'ease_in'
  ease_in_out = 'ease_in_out'

class AnimationLerper:

  def __init__(
    self,
    function: AnimationLerpFunction,
    duration_ms: int,
  ):
    self.__set_function(function)
    self.duration_ms = duration_ms

  def __set_function(self, function: AnimationLerpFunction):
    match(function):
      case AnimationLerpFunction.linear:
        self._interpolator = self._interpolate_linear
      case AnimationLerpFunction.ease_out:
        self._interpolator = self._interpolate_ease_out
      case AnimationLerpFunction.ease_in:
        self._interpolator = self._interpolate_ease_in
      case AnimationLerpFunction.ease_in_out:
        self._interpolator = self._interpolate_ease_in_out

  def _interpolate_ease_in(self, time_elapsed: float):
    return math.pow(time_elapsed / self.duration_ms, 5)


  def _interpolate_ease_out(self, time_elapsed: float):
    time_percent = time_elapsed / self.duration_ms
    return 1 - math.pow(1-time_percent, 5)

  def _interpolate_ease_in_out(self, time_elapsed: float):
    time_percent = time_elapsed / self.duration_ms
    out_val = self._interpolate_ease_out(time_elapsed)
    in_val = self._interpolate_ease_in(time_elapsed)
    return (in_val + (out_val - in_val) * time_percent)

  def _interpolate_linear(self, time_elapsed: float):
    return (time_elapsed / self.duration_ms)

  def interpolate(self, time_elapsed: float):
    if time_elapsed >= self.duration_ms:
      return 1
    elif time_elapsed == 0:
      return 0
    else:
      return self._interpolator(time_elapsed)


class Animator:

  def __init__(
    self,
    lerper: AnimationLerper,
    start_value: float,
    on_frame=None, # callable
    on_stop=None # callable
  ):
    self.is_animating = False
    self.current_value = start_value
    self.target_value = start_value
    self.time_elapsed = 0
    self.lerper = lerper
    self.difference = 0
    self.on_frame = on_frame
    self.on_stop = on_stop

  def start(self, target_value: float):
    self.is_animating = True
    self.time_elapsed = 0
    self.target_value = target_value
    self.difference = target_value - self.current_value

  def frame(self, delta_time: int):
    if not self.is_animating:
      return
    self.time_elapsed += delta_time
    progression = self.lerper.interpolate(self.time_elapsed)
    new_value = self.current_value + (progression * self.difference)
    if progression >= 1:
      self.stop()
    elif self.on_frame:
      self.on_frame(new_value)
    return new_value

  def stop(self):
    self.current_value = self.target_value
    self.is_animating = False
    self.difference = 0
    if self.on_stop:
      self.on_stop(self.current_value)