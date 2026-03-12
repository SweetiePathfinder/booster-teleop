// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from booster_interface:msg/AgentState.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__AGENT_STATE__STRUCT_H_
#define BOOSTER_INTERFACE__MSG__DETAIL__AGENT_STATE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'agent_id'
// Member 'body'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/AgentState in the package booster_interface.
typedef struct booster_interface__msg__AgentState
{
  rosidl_runtime_c__String agent_id;
  rosidl_runtime_c__String body;
} booster_interface__msg__AgentState;

// Struct for a sequence of booster_interface__msg__AgentState.
typedef struct booster_interface__msg__AgentState__Sequence
{
  booster_interface__msg__AgentState * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} booster_interface__msg__AgentState__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__AGENT_STATE__STRUCT_H_
