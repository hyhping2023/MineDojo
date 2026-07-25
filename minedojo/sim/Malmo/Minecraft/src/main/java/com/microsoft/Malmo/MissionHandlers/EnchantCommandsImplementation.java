// --------------------------------------------------------------------------------------------------
//  Copyright (c) 2016 Microsoft Corporation
//  
//  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
//  associated documentation files (the "Software"), to deal in the Software without restriction,
//  including without limitation the rights to use, copy, modify, merge, publish, distribute,
//  sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
//  furnished to do so, subject to the following conditions:
//  
//  The above copyright notice and this permission notice shall be included in all copies or
//  substantial portions of the Software.
//  
//  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
//  NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
//  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
//  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// --------------------------------------------------------------------------------------------------

package com.microsoft.Malmo.MissionHandlers;

import io.netty.buffer.ByteBuf;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.ContainerEnchantment;
import net.minecraft.inventory.Slot;
import net.minecraft.network.play.client.CPacketEnchantItem;
import net.minecraftforge.fml.common.network.ByteBufUtils;
import net.minecraftforge.fml.common.network.simpleimpl.IMessage;
import net.minecraftforge.fml.common.network.simpleimpl.IMessageHandler;
import net.minecraftforge.fml.common.network.simpleimpl.MessageContext;

import com.microsoft.Malmo.MalmoMod;
import com.microsoft.Malmo.Schemas.MissionInit;

/**
 * Enchant commands allow agents to interact with enchantment tables.
 * Commands: "enchant" to open enchantment GUI, "selectEnchant <slot>" to select enchantment slot 0-2.
 */
public class EnchantCommandsImplementation extends CommandBase
{
    private boolean isOverriding;

    public static class EnchantMessage implements IMessage
    {
        String verb;
        String parameter;
        public EnchantMessage()
        {
        }
    
        public EnchantMessage(String verb, String parameter)
        {
            this.verb = verb;
            this.parameter = parameter;
        }

        @Override
        public void fromBytes(ByteBuf buf)
        {
            this.verb = ByteBufUtils.readUTF8String(buf);
            this.parameter = ByteBufUtils.readUTF8String(buf);
        }

        @Override
        public void toBytes(ByteBuf buf)
        {
            ByteBufUtils.writeUTF8String(buf, this.verb);
            ByteBufUtils.writeUTF8String(buf, this.parameter);
        }
    }

    public static class EnchantMessageHandler implements IMessageHandler<EnchantMessage, IMessage>
    {
        @Override
        public IMessage onMessage(final EnchantMessage message, MessageContext ctx)
        {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null)
                return null;

            player.getServer().addScheduledTask(new Runnable()
            {
                @Override
                public void run()
                {
                    if (message.verb.equalsIgnoreCase("enchant"))
                    {
                        // Enable GUI interact for enchanting table
                        MalmoMod.setAllowGuiInteract(true);
                    }
                    else if (message.verb.equalsIgnoreCase("selectEnchant"))
                    {
                        if (player.openContainer instanceof ContainerEnchantment)
                        {
                            try
                            {
                                int slot = Integer.parseInt(message.parameter.trim());
                                if (slot >= 0 && slot <= 2)
                                {
                                    // Send enchant item packet to select the Nth enchantment
                                    player.connection.processEnchantItem(new CPacketEnchantItem(
                                        player.openContainer.windowId, slot));
                                }
                            }
                            catch (NumberFormatException e)
                            {
                                System.out.println("EnchantCommands: invalid enchant slot: " + message.parameter);
                            }
                        }
                        else
                        {
                            System.out.println("EnchantCommands: no enchantment GUI open");
                        }
                    }
                }
            });
            return null;
        }
    }

    @Override
    protected boolean onExecute(String verb, String parameter, MissionInit missionInit)
    {
        if (verb.equalsIgnoreCase("enchant") || verb.equalsIgnoreCase("selectEnchant"))
        {
            MalmoMod.network.sendToServer(new EnchantMessage(verb, parameter));
            return true;
        }
        return false;
    }

    @Override
    public boolean parseParameters(Object params)
    {
        return true;
    }

    @Override
    public void install(MissionInit missionInit)
    {
    }

    @Override
    public void deinstall(MissionInit missionInit)
    {
    }

    @Override
    public boolean isOverriding()
    {
        return this.isOverriding;
    }

    @Override
    public void setOverriding(boolean b)
    {
        this.isOverriding = b;
    }
}
