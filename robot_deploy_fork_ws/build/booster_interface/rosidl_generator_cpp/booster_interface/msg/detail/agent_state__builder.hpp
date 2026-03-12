// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from booster_interface:msg/AgentState.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__AGENT_STATE__BUILDER_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__AGENT_STATE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "booster_interface/msg/detail/agent_state__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace booster_interface
{

namespace msg
{

namespace builder
{

class Init_AgentState_body
{
public:
  explicit Init_AgentState_body(::booster_interface::msg::AgentState & msg)
  : msg_(msg)
  {}
  ::booster_interface::msg::AgentState body(::booster_interface::msg::AgentState::_body_type arg)
  {
    msg_.body = std::move(arg);
    return std::move(msg_);
  }

private:
  ::booster_interface::msg::AgentState msg_;
};

class Init_AgentState_agent_id
{
public:
  Init_AgentState_agent_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_AgentState_body agent_id(::booster_interface::msg::AgentState::_agent_id_type arg)
  {
    msg_.agent_id = std::move(arg);
    return Init_AgentState_body(msg_);
  }

private:
  ::booster_interface::msg::AgentState msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::booster_interface::msg::AgentState>()
{
  return booster_interface::msg::builder::Init_AgentState_agent_id();
}

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__AGENT_STATE__BUILDER_HPP_
