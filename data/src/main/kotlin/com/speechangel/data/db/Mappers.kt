package com.speechangel.data.db

import com.speechangel.core.model.ActionId
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.core.model.VoiceCondition
import com.speechangel.data.FeatureCodec

internal fun CommandEntity.toDomain() = VoiceCommand(
    id = CommandId(id),
    label = label,
    action = ActionId(action),
)

internal fun VoiceCommand.toEntity() = CommandEntity(
    id = id.value,
    label = label,
    action = action.value,
)

internal fun TemplateEntity.toDomain() = Template(
    id = TemplateId(id),
    commandId = CommandId(commandId),
    features = FeatureCodec.decode(features),
    condition = runCatching { VoiceCondition.valueOf(condition) }.getOrDefault(VoiceCondition.OTHER),
    createdAtEpochMs = createdAtEpochMs,
)

internal fun Template.toEntity() = TemplateEntity(
    id = id.value,
    commandId = commandId.value,
    condition = condition.name,
    createdAtEpochMs = createdAtEpochMs,
    features = FeatureCodec.encode(features),
)
